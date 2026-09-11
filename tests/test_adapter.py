"""
Comprehensive Unit & Integration Test Suite for Pharmacy Adapter Bridge
Verifies XML parsing, privacy protection, WWKS2 telemetry, and HA MQTT payload generation.
"""

import os
import sys
import unittest
from datetime import datetime, timezone

# Ensure pharmacy_bridge package is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from pharmacy_bridge.adas_parser import parse_adas_xml, ADASMetrics
from pharmacy_bridge.wwks2_bridge import WWKS2TelemetryTracker, WWKS2State
from pharmacy_bridge.mqtt_publisher import HAMQTTPublisher
from pharmacy_bridge.service import PharmacyAdapterService


class TestADASParser(unittest.TestCase):
    def setUp(self):
        self.samples_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "samples"))

    def test_parse_sample_dws1(self):
        sample_path = os.path.join(self.samples_dir, "sample_adas_dws1.xml")
        self.assertTrue(os.path.exists(sample_path), f"Sample file not found: {sample_path}")
        
        metrics = parse_adas_xml(sample_path)
        self.assertEqual(metrics.header.version, "1.0")
        self.assertEqual(metrics.header.absender, "BGANr1234567")
        self.assertEqual(metrics.header.anbieter, "PHARMATECHNIK")
        self.assertEqual(metrics.header.systembezeichnung, "IXOS")
        self.assertEqual(metrics.total_sales_count, 1)
        self.assertEqual(metrics.total_sales_amount_cents, 1250)

    def test_parse_sample_dws2(self):
        sample_path = os.path.join(self.samples_dir, "sample_adas_dws2.xml")
        self.assertTrue(os.path.exists(sample_path), f"Sample file not found: {sample_path}")
        
        metrics = parse_adas_xml(sample_path)
        self.assertEqual(metrics.total_sales_count, 1)
        self.assertEqual(metrics.goods_receipts_count, 1)
        self.assertEqual(metrics.goods_receipts_amount_cents, 14500)
        self.assertEqual(metrics.total_stock_packs, 120)
        self.assertEqual(metrics.expiring_90d_count, 1)


class TestWWKS2Bridge(unittest.TestCase):
    def setUp(self):
        self.tracker = WWKS2TelemetryTracker(keepalive_timeout_s=90)

    def test_wwks2_hello(self):
        xml_hello = """<?xml version="1.0" encoding="UTF-8"?>
        <Hello Manufacturer="BD Rowa" Product="Vmax" Version="2.4.1" />"""
        state = self.tracker.process_wwks2_xml(xml_hello)
        self.assertTrue(state.online)
        self.assertEqual(state.state, "Ready")
        self.assertEqual(state.manufacturer, "BD Rowa")
        self.assertEqual(state.product, "Vmax")
        self.assertEqual(state.version, "2.4.1")

    def test_wwks2_output_and_derived_kpis(self):
        # Hello
        self.tracker.process_wwks2_xml('<Hello Manufacturer="BD Rowa" Product="Vmax" Version="2.4" />')
        
        # Output 1 (Completed, 8.5s)
        self.tracker.process_wwks2_xml('<OutputMessage Status="Completed" DurationSeconds="8.5" />')
        
        # Output 2 (Completed, 11.5s)
        self.tracker.process_wwks2_xml('<OutputMessage Status="Completed" DurationSeconds="11.5" />')

        # Output 3 (Aborted / Error)
        self.tracker.process_wwks2_xml('<OutputMessage Status="Aborted" />')

        state = self.tracker.state
        self.assertEqual(state.outputs_today, 2)
        self.assertEqual(state.avg_output_time_s_1h, 10.0)
        self.assertGreater(state.error_rate_24h_pct, 0.0)


class TestMQTTPublisher(unittest.TestCase):
    def test_generate_discovery_configs(self):
        pub = HAMQTTPublisher(node_id="ks01")
        configs = pub.generate_discovery_configs()
        self.assertGreater(len(configs), 5)
        
        # Verify online binary sensor config
        topics = [c["topic"] for c in configs]
        self.assertIn("homeassistant/binary_sensor/ks01_online/config", topics)
        self.assertIn("homeassistant/sensor/ks01_state/config", topics)
        self.assertIn("homeassistant/sensor/pharmacy_dws_sales_today/config", topics)


class TestServiceIntegration(unittest.TestCase):
    def test_service_run_pass(self):
        inbox_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_inbox"))
        os.makedirs(inbox_dir, exist_ok=True)
        
        # Copy a sample file into test_inbox
        sample_src = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "samples", "sample_adas_dws1.xml"))
        sample_dst = os.path.join(inbox_dir, "ADAS_DAT_1234567_20260911120000.xml")
        
        with open(sample_src, "r", encoding="utf-8") as f_in:
            content = f_read_content = f_in.read()
        with open(sample_dst, "w", encoding="utf-8") as f_out:
            f_out.write(content)

        service = PharmacyAdapterService(inbox_dir=inbox_dir, node_id="ks01", use_real_mqtt=False)
        service.update()

        self.assertGreater(len(service.published_messages), 5)
        
        # Clean up
        if os.path.exists(sample_dst):
            os.remove(sample_dst)
        if os.path.exists(inbox_dir):
            os.rmdir(inbox_dir)


class TestSimulator(unittest.TestCase):
    def test_simulator_step(self):
        from pharmacy_bridge.simulator import PharmacySimulator
        inbox_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_sim_inbox"))
        simulator = PharmacySimulator(inbox_dir=inbox_dir, mqtt_host="localhost", mqtt_port=1883)
        simulator.service.use_real_mqtt = False
        simulator.step()
        
        self.assertTrue(simulator.service.wwks2_tracker.state.online)
        self.assertGreater(len(simulator.service.published_messages), 0)

        # Cleanup
        for f in os.listdir(inbox_dir):
            os.remove(os.path.join(inbox_dir, f))
        os.rmdir(inbox_dir)


if __name__ == "__main__":
    unittest.main()

