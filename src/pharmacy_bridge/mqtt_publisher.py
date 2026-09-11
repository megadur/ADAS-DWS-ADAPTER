"""
MQTT Auto-Discovery & State Publisher for Home Assistant
Publishes sensor discovery configurations and state updates using HA standard MQTT topics.
"""

import json
import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class HAMQTTPublisher:
    def __init__(self, node_id: str = "ks01", discovery_prefix: str = "homeassistant", state_prefix: str = "pharmacy"):
        self.node_id = node_id
        self.discovery_prefix = discovery_prefix
        self.state_prefix = state_prefix
        self.device_info = {
            "identifiers": [f"apotheke_{node_id}"],
            "name": f"Apotheken Kommissionierer ({node_id})",
            "model": "WWKS2 & ADAS-DWS Adapter",
            "manufacturer": "Pharma Assistant",
            "sw_version": "1.0.0"
        }

    def generate_discovery_configs(self) -> List[Dict[str, Any]]:
        """
        Generates Home Assistant MQTT Discovery configuration dictionaries for all sensors.
        """
        base_state_topic = f"{self.state_prefix}/{self.node_id}/metrics"
        availability_topic = f"{self.state_prefix}/{self.node_id}/availability"

        configs = [
            # Binary Sensor: Online Status
            {
                "topic": f"{self.discovery_prefix}/binary_sensor/{self.node_id}_online/config",
                "payload": {
                    "name": "Kommissionierer Online",
                    "unique_id": f"{self.node_id}_online",
                    "state_topic": availability_topic,
                    "payload_on": "online",
                    "payload_off": "offline",
                    "device_class": "connectivity",
                    "device": self.device_info
                }
            },
            # Sensor: Automaten Status
            {
                "topic": f"{self.discovery_prefix}/sensor/{self.node_id}_state/config",
                "payload": {
                    "name": "Kommissionierer Status",
                    "unique_id": f"{self.node_id}_state",
                    "state_topic": base_state_topic,
                    "value_template": "{{ value_json.state }}",
                    "availability_topic": availability_topic,
                    "icon": "mdi:robot-industrial",
                    "device": self.device_info
                }
            },
            # Sensor: Aktive Tasks
            {
                "topic": f"{self.discovery_prefix}/sensor/{self.node_id}_active_tasks/config",
                "payload": {
                    "name": "Aktive Aufträge",
                    "unique_id": f"{self.node_id}_active_tasks",
                    "state_topic": base_state_topic,
                    "value_template": "{{ value_json.active_tasks }}",
                    "unit_of_measurement": "Aufträge",
                    "state_class": "measurement",
                    "icon": "mdi:tray-full",
                    "device": self.device_info
                }
            },
            # Sensor: Auslagerungen Heute
            {
                "topic": f"{self.discovery_prefix}/sensor/{self.node_id}_outputs_today/config",
                "payload": {
                    "name": "Auslagerungen Heute",
                    "unique_id": f"{self.node_id}_outputs_today",
                    "state_topic": base_state_topic,
                    "value_template": "{{ value_json.outputs_today }}",
                    "unit_of_measurement": "Packungen",
                    "state_class": "measurement",
                    "icon": "mdi:package-up",
                    "device": self.device_info
                }
            },
            # Sensor: Einlagerungen Heute
            {
                "topic": f"{self.discovery_prefix}/sensor/{self.node_id}_inputs_today/config",
                "payload": {
                    "name": "Einlagerungen Heute",
                    "unique_id": f"{self.node_id}_inputs_today",
                    "state_topic": base_state_topic,
                    "value_template": "{{ value_json.inputs_today }}",
                    "unit_of_measurement": "Packungen",
                    "state_class": "measurement",
                    "icon": "mdi:package-down",
                    "device": self.device_info
                }
            },
            # Sensor: Auslagerungsdauer (1h Mittelwert)
            {
                "topic": f"{self.discovery_prefix}/sensor/{self.node_id}_avg_output_time_1h/config",
                "payload": {
                    "name": "Auslagerungsdauer 1h",
                    "unique_id": f"{self.node_id}_avg_output_time_1h",
                    "state_topic": base_state_topic,
                    "value_template": "{{ value_json.avg_output_time_s_1h }}",
                    "unit_of_measurement": "s",
                    "device_class": "duration",
                    "state_class": "measurement",
                    "icon": "mdi:timer-outline",
                    "device": self.device_info
                }
            },
            # Sensor: Fehlerquote 24h (%)
            {
                "topic": f"{self.discovery_prefix}/sensor/{self.node_id}_error_rate_24h/config",
                "payload": {
                    "name": "Fehlerquote 24h",
                    "unique_id": f"{self.node_id}_error_rate_24h",
                    "state_topic": base_state_topic,
                    "value_template": "{{ value_json.error_rate_24h_pct }}",
                    "unit_of_measurement": "%",
                    "state_class": "measurement",
                    "icon": "mdi:alert-circle-outline",
                    "device": self.device_info
                }
            },
            # Sensor: WWS Gesamtverkäufe Heute
            {
                "topic": f"{self.discovery_prefix}/sensor/pharmacy_dws_sales_today/config",
                "payload": {
                    "name": "WWS Verkäufe Heute",
                    "unique_id": "pharmacy_dws_sales_today",
                    "state_topic": f"{self.state_prefix}/dws/metrics",
                    "value_template": "{{ value_json.total_sales_count }}",
                    "unit_of_measurement": "Bons",
                    "state_class": "measurement",
                    "icon": "mdi:receipt",
                    "device": self.device_info
                }
            },
            # Sensor: WWS Lagerbestände (Packungen)
            {
                "topic": f"{self.discovery_prefix}/sensor/pharmacy_dws_stock_packs/config",
                "payload": {
                    "name": "WWS Lagerbestand",
                    "unique_id": "pharmacy_dws_stock_packs",
                    "state_topic": f"{self.state_prefix}/dws/metrics",
                    "value_template": "{{ value_json.total_stock_packs }}",
                    "unit_of_measurement": "Packungen",
                    "state_class": "measurement",
                    "icon": "mdi:boxes",
                    "device": self.device_info
                }
            },
            # Sensor: WWS Verfall in <= 90 Tagen
            {
                "topic": f"{self.discovery_prefix}/sensor/pharmacy_dws_expiring_90d/config",
                "payload": {
                    "name": "Verfall in 90 Tagen",
                    "unique_id": "pharmacy_dws_expiring_90d",
                    "state_topic": f"{self.state_prefix}/dws/metrics",
                    "value_template": "{{ value_json.expiring_90d_count }}",
                    "unit_of_measurement": "Artikel",
                    "state_class": "measurement",
                    "icon": "mdi:calendar-clock",
                    "device": self.device_info
                }
            }
        ]

        return configs

    def publish(self, publish_func: Callable[[str, str, bool], None], wwks2_state_dict: Dict[str, Any], adas_metrics_dict: Dict[str, Any]):
        """
        Publishes discovery configs and state telemetry to MQTT using the provided callback.
        """
        # Publish Discovery
        for cfg in self.generate_discovery_configs():
            topic = cfg["topic"]
            payload = json.dumps(cfg["payload"], ensure_ascii=False)
            publish_func(topic, payload, True)

        # Publish Availability
        availability_topic = f"{self.state_prefix}/{self.node_id}/availability"
        is_online = wwks2_state_dict.get("online", False)
        publish_func(availability_topic, "online" if is_online else "offline", True)

        # Publish WWKS2 Metrics State
        wwks2_state_topic = f"{self.state_prefix}/{self.node_id}/metrics"
        publish_func(wwks2_state_topic, json.dumps(wwks2_state_dict, ensure_ascii=False), True)

        # Publish ADAS-DWS Metrics State
        adas_state_topic = f"{self.state_prefix}/dws/metrics"
        publish_func(adas_state_topic, json.dumps(adas_metrics_dict, ensure_ascii=False), True)
