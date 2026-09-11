"""
Main Service Daemon for Pharmacy Adapter Bridge
Watches inbox directory for ADAS-DWS XML export files, runs WWKS2 telemetry,
and publishes state updates to Home Assistant via MQTT.
"""

import argparse
from dataclasses import asdict
import glob
import logging
import os
import sys
import time
from typing import Optional

try:
    import paho.mqtt.client as mqtt
    PAHO_AVAILABLE = True
except ImportError:
    PAHO_AVAILABLE = False

from pharmacy_bridge.adas_parser import parse_adas_xml, ADASMetrics
from pharmacy_bridge.mqtt_publisher import HAMQTTPublisher
from pharmacy_bridge.wwks2_bridge import WWKS2TelemetryTracker

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("pharmacy_service")


class PharmacyAdapterService:
    def __init__(self, inbox_dir: str, mqtt_host: str = "localhost", mqtt_port: int = 1883, node_id: str = "ks01", use_real_mqtt: bool = True):
        self.inbox_dir = inbox_dir
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        self.node_id = node_id
        self.use_real_mqtt = use_real_mqtt and PAHO_AVAILABLE
        
        self.wwks2_tracker = WWKS2TelemetryTracker()
        self.mqtt_publisher = HAMQTTPublisher(node_id=node_id)
        self.latest_adas_metrics = ADASMetrics()
        self.published_messages = []

        self.mqtt_client = None
        if self.use_real_mqtt:
            self._connect_mqtt()

    def _connect_mqtt(self):
        try:
            # Handle paho-mqtt v1 vs v2 compatibility
            try:
                self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, f"pharmacy_bridge_{self.node_id}")
            except AttributeError:
                self.mqtt_client = mqtt.Client(f"pharmacy_bridge_{self.node_id}")
                
            self.mqtt_client.connect(self.mqtt_host, self.mqtt_port, keepalive=60)
            self.mqtt_client.loop_start()
            logger.info(f"Connected to MQTT Broker at {self.mqtt_host}:{self.mqtt_port}")
        except Exception as e:
            logger.warning(f"Could not connect to real MQTT broker at {self.mqtt_host}:{self.mqtt_port} ({e}). Falling back to local mock publish.")
            self.mqtt_client = None

    def real_mqtt_publish(self, topic: str, payload: str, retain: bool = False):
        """Publishes message to network MQTT broker."""
        self.published_messages.append({"topic": topic, "payload": payload, "retain": retain})
        if self.mqtt_client:
            try:
                info = self.mqtt_client.publish(topic, payload, qos=1, retain=retain)
                info.wait_for_publish(timeout=2.0)
                logger.debug(f"[MQTT REAL PUB] {topic} (retain={retain}) -> OK")
            except Exception as e:
                logger.error(f"Error publishing MQTT to {topic}: {e}")
        else:
            self.mock_mqtt_publish(topic, payload, retain)

    def mock_mqtt_publish(self, topic: str, payload: str, retain: bool = False):
        """Fallback publish handler for offline/test mode."""
        logger.debug(f"[MQTT MOCK PUB] {topic} (retain={retain}): {payload}")
        self.published_messages.append({"topic": topic, "payload": payload, "retain": retain})

    def process_inbox(self):
        """Scans inbox_dir for ADAS_DAT_*.xml files and processes them."""
        if not os.path.exists(self.inbox_dir):
            os.makedirs(self.inbox_dir, exist_ok=True)
            return

        xml_files = glob.glob(os.path.join(self.inbox_dir, "*.xml"))
        for xml_file in xml_files:
            logger.info(f"Processing ADAS XML file: {xml_file}")
            try:
                metrics = parse_adas_xml(xml_file)
                self.latest_adas_metrics = metrics
                logger.info(f"Parsed ADAS XML successfully. Total sales count: {metrics.total_sales_count}, Stock packs: {metrics.total_stock_packs}")
            except Exception as e:
                logger.error(f"Error processing {xml_file}: {e}")
            finally:
                try:
                    os.remove(xml_file)
                except Exception:
                    pass

    def update(self, publish_callback=None):
        """Performs a single telemetry and ADAS sync cycle."""
        if publish_callback is None:
            publish_callback = self.real_mqtt_publish if self.mqtt_client else self.mock_mqtt_publish

        self.process_inbox()
        self.wwks2_tracker.check_liveness()
        
        wwks2_dict = asdict(self.wwks2_tracker.state)
        if wwks2_dict.get("last_telegram_utc"):
            wwks2_dict["last_telegram_utc"] = wwks2_dict["last_telegram_utc"].isoformat()
        if wwks2_dict.get("last_successful_output_utc"):
            wwks2_dict["last_successful_output_utc"] = wwks2_dict["last_successful_output_utc"].isoformat()

        adas_dict = asdict(self.latest_adas_metrics)
        
        self.mqtt_publisher.publish(publish_callback, wwks2_dict, adas_dict)


def main():
    parser = argparse.ArgumentParser(description="Apotheken Home Assistant MQTT Adapter Service")
    parser.add_argument("--inbox", default="./inbox", help="Path to ADAS-DWS XML inbox directory")
    parser.add_argument("--mqtt-host", default="localhost", help="MQTT Broker hostname / IP")
    parser.add_argument("--mqtt-port", type=int, default=1883, help="MQTT Broker port")
    parser.add_argument("--node-id", default="ks01", help="Node ID / Unique Identifier")
    parser.add_argument("--once", action="store_true", help="Run single pass and exit")
    args = parser.parse_args()

    service = PharmacyAdapterService(inbox_dir=args.inbox, mqtt_host=args.mqtt_host, mqtt_port=args.mqtt_port, node_id=args.node_id)
    logger.info("Starting Pharmacy Adapter Service...")
    
    if args.once:
        service.update()
        logger.info("Single pass complete.")
    else:
        try:
            while True:
                service.update()
                time.sleep(10)
        except KeyboardInterrupt:
            logger.info("Service stopped by user.")


if __name__ == "__main__":
    main()
