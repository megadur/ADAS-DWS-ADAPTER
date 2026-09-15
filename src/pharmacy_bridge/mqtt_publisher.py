"""
MQTT Auto-Discovery & State Publisher for Home Assistant
Publishes sensor discovery configurations with explicit object_id and state updates using HA standard MQTT topics.
Exposes 20+ sensors across WWKS2 and ADAS-DWS data models.
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
        Generates Home Assistant MQTT Discovery configuration dictionaries for all 20+ sensors.
        """
        base_state_topic = f"{self.state_prefix}/{self.node_id}/metrics"
        availability_topic = f"{self.state_prefix}/{self.node_id}/availability"
        dws_state_topic = f"{self.state_prefix}/dws/metrics"

        configs = [
            # --- WWKS2 Sensors ---
            {
                "topic": f"{self.discovery_prefix}/binary_sensor/{self.node_id}_online/config",
                "payload": {
                    "name": "Kommissionierer Online",
                    "object_id": f"{self.node_id}_online",
                    "unique_id": f"{self.node_id}_online",
                    "state_topic": availability_topic,
                    "payload_on": "online",
                    "payload_off": "offline",
                    "device_class": "connectivity",
                    "device": self.device_info
                }
            },
            {
                "topic": f"{self.discovery_prefix}/sensor/{self.node_id}_state/config",
                "payload": {
                    "name": "Kommissionierer Status",
                    "object_id": f"{self.node_id}_state",
                    "unique_id": f"{self.node_id}_state",
                    "state_topic": base_state_topic,
                    "value_template": "{{ value_json.state }}",
                    "availability_topic": availability_topic,
                    "icon": "mdi:robot-industrial",
                    "device": self.device_info
                }
            },
            {
                "topic": f"{self.discovery_prefix}/sensor/{self.node_id}_active_tasks/config",
                "payload": {
                    "name": "Aktive Aufträge",
                    "object_id": f"{self.node_id}_active_tasks",
                    "unique_id": f"{self.node_id}_active_tasks",
                    "state_topic": base_state_topic,
                    "value_template": "{{ value_json.active_tasks }}",
                    "unit_of_measurement": "Aufträge",
                    "state_class": "measurement",
                    "icon": "mdi:tray-full",
                    "device": self.device_info
                }
            },
            {
                "topic": f"{self.discovery_prefix}/sensor/{self.node_id}_queued_tasks/config",
                "payload": {
                    "name": "Wartende Aufträge (Queue)",
                    "object_id": f"{self.node_id}_queued_tasks",
                    "unique_id": f"{self.node_id}_queued_tasks",
                    "state_topic": base_state_topic,
                    "value_template": "{{ value_json.queued_tasks }}",
                    "unit_of_measurement": "Aufträge",
                    "state_class": "measurement",
                    "icon": "mdi:clock-outline",
                    "device": self.device_info
                }
            },
            {
                "topic": f"{self.discovery_prefix}/sensor/{self.node_id}_outputs_today/config",
                "payload": {
                    "name": "Auslagerungen Heute",
                    "object_id": f"{self.node_id}_outputs_today",
                    "unique_id": f"{self.node_id}_outputs_today",
                    "state_topic": base_state_topic,
                    "value_template": "{{ value_json.outputs_today }}",
                    "unit_of_measurement": "Packungen",
                    "state_class": "measurement",
                    "icon": "mdi:package-up",
                    "device": self.device_info
                }
            },
            {
                "topic": f"{self.discovery_prefix}/sensor/{self.node_id}_inputs_today/config",
                "payload": {
                    "name": "Einlagerungen Heute",
                    "object_id": f"{self.node_id}_inputs_today",
                    "unique_id": f"{self.node_id}_inputs_today",
                    "state_topic": base_state_topic,
                    "value_template": "{{ value_json.inputs_today }}",
                    "unit_of_measurement": "Packungen",
                    "state_class": "measurement",
                    "icon": "mdi:package-down",
                    "device": self.device_info
                }
            },
            {
                "topic": f"{self.discovery_prefix}/sensor/{self.node_id}_avg_output_time_1h/config",
                "payload": {
                    "name": "Auslagerungsdauer 1h",
                    "object_id": f"{self.node_id}_avg_output_time_1h",
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
            {
                "topic": f"{self.discovery_prefix}/sensor/{self.node_id}_p95_output_time_24h/config",
                "payload": {
                    "name": "Auslagerungsdauer P95 24h",
                    "object_id": f"{self.node_id}_p95_output_time_24h",
                    "unique_id": f"{self.node_id}_p95_output_time_24h",
                    "state_topic": base_state_topic,
                    "value_template": "{{ value_json.p95_output_time_s_24h }}",
                    "unit_of_measurement": "s",
                    "device_class": "duration",
                    "state_class": "measurement",
                    "icon": "mdi:timer-sand",
                    "device": self.device_info
                }
            },
            {
                "topic": f"{self.discovery_prefix}/sensor/{self.node_id}_error_rate_24h/config",
                "payload": {
                    "name": "Fehlerquote 24h",
                    "object_id": f"{self.node_id}_error_rate_24h",
                    "unique_id": f"{self.node_id}_error_rate_24h",
                    "state_topic": base_state_topic,
                    "value_template": "{{ value_json.error_rate_24h_pct }}",
                    "unit_of_measurement": "%",
                    "state_class": "measurement",
                    "icon": "mdi:alert-circle-outline",
                    "device": self.device_info
                }
            },

            # --- ADAS-DWS WWS Controlling Sensors ---
            {
                "topic": f"{self.discovery_prefix}/sensor/pharmacy_dws_sales_today/config",
                "payload": {
                    "name": "WWS Verkäufe Heute",
                    "object_id": "pharmacy_dws_sales_today",
                    "unique_id": "pharmacy_dws_sales_today",
                    "state_topic": dws_state_topic,
                    "value_template": "{{ value_json.total_sales_count }}",
                    "unit_of_measurement": "Bons",
                    "state_class": "measurement",
                    "icon": "mdi:receipt",
                    "device": self.device_info
                }
            },
            {
                "topic": f"{self.discovery_prefix}/sensor/pharmacy_dws_sales_amount_eur/config",
                "payload": {
                    "name": "WWS Tagesumsatz EUR",
                    "object_id": "pharmacy_dws_sales_amount_eur",
                    "unique_id": "pharmacy_dws_sales_amount_eur",
                    "state_topic": dws_state_topic,
                    "value_template": "{{ (value_json.total_sales_amount_cents / 100) | round(2) }}",
                    "unit_of_measurement": "€",
                    "device_class": "monetary",
                    "state_class": "measurement",
                    "icon": "mdi:currency-eur",
                    "device": self.device_info
                }
            },
            {
                "topic": f"{self.discovery_prefix}/sensor/pharmacy_dws_stock_packs/config",
                "payload": {
                    "name": "WWS Lagerbestand",
                    "object_id": "pharmacy_dws_stock_packs",
                    "unique_id": "pharmacy_dws_stock_packs",
                    "state_topic": dws_state_topic,
                    "value_template": "{{ value_json.total_stock_packs }}",
                    "unit_of_measurement": "Packungen",
                    "state_class": "measurement",
                    "icon": "mdi:boxes",
                    "device": self.device_info
                }
            },
            {
                "topic": f"{self.discovery_prefix}/sensor/pharmacy_dws_expiring_90d/config",
                "payload": {
                    "name": "Verfall in 90 Tagen",
                    "object_id": "pharmacy_dws_expiring_90d",
                    "unique_id": "pharmacy_dws_expiring_90d",
                    "state_topic": dws_state_topic,
                    "value_template": "{{ value_json.expiring_90d_count }}",
                    "unit_of_measurement": "Artikel",
                    "state_class": "measurement",
                    "icon": "mdi:calendar-clock",
                    "device": self.device_info
                }
            },
            {
                "topic": f"{self.discovery_prefix}/sensor/pharmacy_dws_old_stock_180d/config",
                "payload": {
                    "name": "Altbestand 180 Tage",
                    "object_id": "pharmacy_dws_old_stock_180d",
                    "unique_id": "pharmacy_dws_old_stock_180d",
                    "state_topic": dws_state_topic,
                    "value_template": "{{ value_json.old_stock_180d_count }}",
                    "unit_of_measurement": "Artikel",
                    "state_class": "measurement",
                    "icon": "mdi:history",
                    "device": self.device_info
                }
            },
            {
                "topic": f"{self.discovery_prefix}/sensor/pharmacy_dws_goods_receipts_packs/config",
                "payload": {
                    "name": "Wareneingang Heute",
                    "object_id": "pharmacy_dws_goods_receipts_packs",
                    "unique_id": "pharmacy_dws_goods_receipts_packs",
                    "state_topic": dws_state_topic,
                    "value_template": "{{ value_json.goods_receipts_packs }}",
                    "unit_of_measurement": "Packungen",
                    "state_class": "measurement",
                    "icon": "mdi:truck-delivery",
                    "device": self.device_info
                }
            },
            {
                "topic": f"{self.discovery_prefix}/sensor/pharmacy_dws_missed_sales/config",
                "payload": {
                    "name": "Neinverkäufe Heute",
                    "object_id": "pharmacy_dws_missed_sales",
                    "unique_id": "pharmacy_dws_missed_sales",
                    "state_topic": dws_state_topic,
                    "value_template": "{{ value_json.missed_sales_count }}",
                    "unit_of_measurement": "Anfragen",
                    "state_class": "measurement",
                    "icon": "mdi:close-circle-outline",
                    "device": self.device_info
                }
            },
            {
                "topic": f"{self.discovery_prefix}/sensor/pharmacy_dws_returns/config",
                "payload": {
                    "name": "Retouren Heute",
                    "object_id": "pharmacy_dws_returns",
                    "unique_id": "pharmacy_dws_returns",
                    "state_topic": dws_state_topic,
                    "value_template": "{{ value_json.returns_count }}",
                    "unit_of_measurement": "Belege",
                    "state_class": "measurement",
                    "icon": "mdi:keyboard-return",
                    "device": self.device_info
                }
            },

            # --- Pharmacy Core Finance & 7-Day Liquidity Forecast Sensors ---
            {
                "topic": f"{self.discovery_prefix}/sensor/pharmacy_bank_balance/config",
                "payload": {
                    "name": "Bankkontostand Heute",
                    "object_id": "pharmacy_bank_balance",
                    "unique_id": "pharmacy_bank_balance",
                    "state_topic": f"{self.state_prefix}/core/metrics",
                    "value_template": "{{ value_json.bank_balance_eur }}",
                    "unit_of_measurement": "€",
                    "device_class": "monetary",
                    "state_class": "measurement",
                    "icon": "mdi:bank",
                    "device": self.device_info
                }
            },
            {
                "topic": f"{self.discovery_prefix}/sensor/pharmacy_arz_receivables_7d/config",
                "payload": {
                    "name": "ARZ Auszahlungen (7T)",
                    "object_id": "pharmacy_arz_receivables_7d",
                    "unique_id": "pharmacy_arz_receivables_7d",
                    "state_topic": f"{self.state_prefix}/core/metrics",
                    "value_template": "{{ value_json.arz_receivables_7d_eur }}",
                    "unit_of_measurement": "€",
                    "device_class": "monetary",
                    "state_class": "measurement",
                    "icon": "mdi:cash-plus",
                    "device": self.device_info
                }
            },
            {
                "topic": f"{self.discovery_prefix}/sensor/pharmacy_wholesaler_payables_7d/config",
                "payload": {
                    "name": "Großhandelsfälligkeiten (7T)",
                    "object_id": "pharmacy_wholesaler_payables_7d",
                    "unique_id": "pharmacy_wholesaler_payables_7d",
                    "state_topic": f"{self.state_prefix}/core/metrics",
                    "value_template": "{{ value_json.wholesaler_payables_7d_eur }}",
                    "unit_of_measurement": "€",
                    "device_class": "monetary",
                    "state_class": "measurement",
                    "icon": "mdi:cash-minus",
                    "device": self.device_info
                }
            },
            {
                "topic": f"{self.discovery_prefix}/sensor/pharmacy_projected_liquidity_7d/config",
                "payload": {
                    "name": "Prognostizierte Liquidität (7T)",
                    "object_id": "pharmacy_projected_liquidity_7d",
                    "unique_id": "pharmacy_projected_liquidity_7d",
                    "state_topic": f"{self.state_prefix}/core/metrics",
                    "value_template": "{{ value_json.projected_liquidity_7d_eur }}",
                    "unit_of_measurement": "€",
                    "device_class": "monetary",
                    "state_class": "measurement",
                    "icon": "mdi:chart-timeline-variant",
                    "device": self.device_info
                }
            },
            {
                "topic": f"{self.discovery_prefix}/binary_sensor/pharmacy_liquidity_warning/config",
                "payload": {
                    "name": "Liquiditätsengpass Warnung",
                    "object_id": "pharmacy_liquidity_warning",
                    "unique_id": "pharmacy_liquidity_warning",
                    "state_topic": f"{self.state_prefix}/core/metrics",
                    "value_template": "{{ 'ON' if value_json.is_liquidity_warning else 'OFF' }}",
                    "device_class": "problem",
                    "icon": "mdi:alert-decagram",
                    "device": self.device_info
                }
            }
        ]

        return configs

    def publish(self, publish_func: Callable[[str, str, bool], None], wwks2_state_dict: Dict[str, Any], adas_metrics_dict: Dict[str, Any], core_finance_dict: Optional[Dict[str, Any]] = None):
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

        # Publish Pharmacy Core Finance Metrics State
        if core_finance_dict:
            core_state_topic = f"{self.state_prefix}/core/metrics"
            publish_func(core_state_topic, json.dumps(core_finance_dict, ensure_ascii=False), True)

