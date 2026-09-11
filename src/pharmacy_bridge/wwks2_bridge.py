"""
WWKS2 Telemetry & State Machine Bridge
Processes WWKS2 XML protocol messages (Hello, KeepAlive, StatusRequest/Response, TaskInfo, OutputMessage).
Maintains rolling window metrics:
  - Online status & state ('Ready', 'NotReady', 'Offline', 'Maintenance')
  - Active task count (Queued + InProcess)
  - Output duration metrics (1h rolling average)
  - Error rate (24h rolling percentage)
"""

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Dict, List, Optional
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)


@dataclass
class WWKS2State:
    online: bool = False
    state: str = "Offline"  # Ready, NotReady, Maintenance, Offline
    active_tasks: int = 0
    queued_tasks: int = 0
    in_process_tasks: int = 0
    outputs_today: int = 0
    inputs_today: int = 0
    avg_output_time_s_1h: float = 0.0
    p95_output_time_s_24h: float = 0.0
    error_rate_24h_pct: float = 0.0
    last_telegram_utc: Optional[datetime] = None
    last_successful_output_utc: Optional[datetime] = None
    manufacturer: str = "Unknown"
    product: str = "Unknown"
    version: str = "Unknown"


class WWKS2TelemetryTracker:
    def __init__(self, keepalive_timeout_s: int = 90):
        self.keepalive_timeout_s = keepalive_timeout_s
        self.state = WWKS2State()
        
        # Rolling windows for metrics
        # Output duration entries: (timestamp_utc, duration_seconds)
        self._output_durations_1h = deque()
        self._output_durations_24h = deque()
        
        # Completed / aborted tasks in 24h: (timestamp_utc, is_error: bool)
        self._task_results_24h = deque()

    def process_wwks2_xml(self, xml_string: str) -> WWKS2State:
        """
        Parses a WWKS2 XML message string and updates live telemetry state.
        """
        now = datetime.now(timezone.utc)
        self.state.last_telegram_utc = now
        self.state.online = True

        try:
            root = ET.fromstring(xml_string.strip())
        except Exception as e:
            logger.error(f"Failed to parse WWKS2 XML message: {e}")
            return self.state

        tag_name = root.tag.split('}', 1)[1] if '}' in root.tag else root.tag

        if tag_name == 'Hello':
            self._handle_hello(root)
        elif tag_name in ('StatusResponse', 'StatusMessage'):
            self._handle_status(root)
        elif tag_name == 'TaskInfo':
            self._handle_task_info(root, now)
        elif tag_name in ('OutputMessage', 'OutputResponse'):
            self._handle_output(root, now)
        elif tag_name == 'InputMessage':
            self._handle_input(root)
        elif tag_name == 'KeepAlive':
            self.state.online = True

        self._prune_rolling_windows(now)
        self._update_derived_kpis()
        return self.state

    def _handle_hello(self, elem: ET.Element):
        self.state.manufacturer = elem.get('Manufacturer', self.state.manufacturer)
        self.state.product = elem.get('Product', self.state.product)
        self.state.version = elem.get('Version', self.state.version)
        self.state.state = "Ready"

    def _handle_status(self, elem: ET.Element):
        st = elem.get('State', 'Ready')
        if st in ('Ready', 'NotReady', 'Maintenance', 'Offline'):
            self.state.state = st
        else:
            self.state.state = 'NotReady' if st != '0' else 'Ready'

    def _handle_task_info(self, elem: ET.Element, now: datetime):
        status = elem.get('Status', '')
        queued = 0
        in_proc = 0

        for child in elem:
            c_tag = child.tag.split('}', 1)[1] if '}' in child.tag else child.tag
            if c_tag == 'Task':
                t_status = child.get('Status', '')
                if t_status == 'Queued':
                    queued += 1
                elif t_status == 'InProcess':
                    in_proc += 1
                elif t_status in ('Completed', 'Incomplete', 'Aborted'):
                    is_err = t_status in ('Incomplete', 'Aborted')
                    self._task_results_24h.append((now, is_err))

        self.state.queued_tasks = queued
        self.state.in_process_tasks = in_proc
        self.state.active_tasks = queued + in_proc

    def _handle_output(self, elem: ET.Element, now: datetime):
        status = elem.get('Status', 'Completed')
        duration_s = elem.get('DurationSeconds')

        if status == 'Completed':
            self.state.outputs_today += 1
            self.state.last_successful_output_utc = now
            self._task_results_24h.append((now, False))
        elif status in ('Incomplete', 'Aborted'):
            self._task_results_24h.append((now, True))

        if duration_s is not None:
            try:
                dur = float(duration_s)
                self._output_durations_1h.append((now, dur))
                self._output_durations_24h.append((now, dur))
            except ValueError:
                pass

    def _handle_input(self, elem: ET.Element):
        status = elem.get('Status', 'Completed')
        if status == 'Completed':
            self.state.inputs_today += 1

    def check_liveness(self) -> bool:
        """Call periodically to check whether last message received is within keepalive window."""
        if self.state.last_telegram_utc is None:
            self.state.online = False
            self.state.state = "Offline"
            return False
            
        elapsed = (datetime.now(timezone.utc) - self.state.last_telegram_utc).total_seconds()
        if elapsed > self.keepalive_timeout_s:
            self.state.online = False
            self.state.state = "Offline"
            return False
            
        self.state.online = True
        return True

    def _prune_rolling_windows(self, now: datetime):
        cutoff_1h = now.timestamp() - 3600
        cutoff_24h = now.timestamp() - 86400

        while self._output_durations_1h and self._output_durations_1h[0][0].timestamp() < cutoff_1h:
            self._output_durations_1h.popleft()

        while self._output_durations_24h and self._output_durations_24h[0][0].timestamp() < cutoff_24h:
            self._output_durations_24h.popleft()

        while self._task_results_24h and self._task_results_24h[0][0].timestamp() < cutoff_24h:
            self._task_results_24h.popleft()

    def _update_derived_kpis(self):
        # 1h Avg Output Duration
        if self._output_durations_1h:
            avg_dur = sum(dur for _, dur in self._output_durations_1h) / len(self._output_durations_1h)
            self.state.avg_output_time_s_1h = round(avg_dur, 2)
        else:
            self.state.avg_output_time_s_1h = 0.0

        # 24h P95 Output Duration
        if self._output_durations_24h:
            sorted_durs = sorted(dur for _, dur in self._output_durations_24h)
            p95_idx = int(0.95 * len(sorted_durs))
            self.state.p95_output_time_s_24h = round(sorted_durs[min(p95_idx, len(sorted_durs) - 1)], 2)
        else:
            self.state.p95_output_time_s_24h = 0.0

        # 24h Error Rate Percentage
        if self._task_results_24h:
            err_count = sum(1 for _, is_err in self._task_results_24h if is_err)
            pct = (err_count / len(self._task_results_24h)) * 100.0
            self.state.error_rate_24h_pct = round(pct, 2)
        else:
            self.state.error_rate_24h_pct = 0.0
