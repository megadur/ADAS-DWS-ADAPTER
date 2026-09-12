"""
Apotheken Simulator & Mock Data Generator
Simulates full 26-parameter pharmacy metrics:
1. WWKS2 live events (Hello, KeepAlive, OutputMessage, TaskInfo, StatusResponse)
2. ADAS-DWS XML export file generation (Verkäufe, Wareneingang, Lagerbestand, Verfallsdaten, Retouren, Neinverkäufe)

Generates dynamic, live-updating metrics with high activity for Home Assistant dashboards & Web UI.
"""

import argparse
from datetime import datetime, timezone
import logging
import math
import os
import random
import time

from .wwks2_bridge import WWKS2TelemetryTracker
from .adas_parser import parse_adas_xml, ADASMetrics, ADASHeader
from .service import PharmacyAdapterService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("pharmacy_simulator")


class PharmacySimulator:
    def __init__(self, inbox_dir: str = "./inbox", mqtt_host: str = "localhost", mqtt_port: int = 1883, node_id: str = "ks01"):
        self.inbox_dir = inbox_dir
        self.node_id = node_id
        self.service = PharmacyAdapterService(inbox_dir=inbox_dir, mqtt_host=mqtt_host, mqtt_port=mqtt_port, node_id=node_id)
        
        # Cumulative live counters
        self.sales_count = 145
        self.sales_cents = 348500  # 3,485.00 €
        self.items_sold = 210
        self.stock_packs = 18450
        self.expiring_90d = 34
        self.old_stock_180d = 12
        self.goods_receipts_count = 4
        self.goods_receipts_packs = 280
        self.goods_receipts_cents = 145000
        self.returns_count = 2
        self.returns_cents = 18500
        self.missed_sales_count = 5
        self.missed_sales_packs = 7
        
        self.step_counter = 0

        # Initialize WWKS2 with Hello
        self.service.wwks2_tracker.process_wwks2_xml(
            '<Hello Manufacturer="BD Rowa (Simulated)" Product="Vmax" Version="2.4.1" />'
        )

    def generate_mock_adas_xml(self, filepath: str):
        """Generates a realistic ADAS-DWS v1.0 Ausbaustufe 2/3 XML file with all simulated metrics."""
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        
        xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<adwsroot xmlns="http://www.adas.de/spec/dws/v1">
	<kopf>
		<version>1.0</version>
		<absender>BGANr1234567</absender>
		<erstelltAm>{now_iso}</erstelltAm>
		<instanzId>Server-Sim</instanzId>
		<system>
			<anbieter>PHARMATECHNIK</anbieter>
			<systembezeichnung>IXOS (Simuliert)</systembezeichnung>
		</system>
	</kopf>
	<verkaufsblock>
"""
        # Add sales totals
        sales_chunk = min(self.sales_count, 10)
        for i in range(sales_chunk):
            sale_vk = self.sales_cents // self.sales_count if self.sales_count > 0 else 1250
            xml_content += f"""		<total>
			<totalNr>SIM-TOT-{1000 + i}</totalNr>
			<verarbeitetAm>{now_iso}</verarbeitetAm>
			<buchungAm>{now_iso}</buchungAm>
			<subtotal>
				<storno>false</storno>
				<verkaufsart>Normalverkauf</verkaufsart>
				<subtotalzeile>
					<pzn>0{random.randint(1000000, 9999999)}</pzn>
					<name>Simulierte Packung OTC {i+1}</name>
					<menge>1</menge>
					<einheit>ST</einheit>
					<ampreisvAmg>0</ampreisvAmg>
					<ampreisvSgb>0</ampreisvSgb>
					<btm>0</btm>
					<abdaWarengruppe>OTC</abdaWarengruppe>
					<darreichungsform>TAB</darreichungsform>
					<anbieter>12345</anbieter>
					<lagertemperaturMin>15</lagertemperaturMin>
					<lagertemperaturMax>25</lagertemperaturMax>
					<notfalldepot>0</notfalldepot>
					<abgaberegelung>Apothekenpflicht</abgaberegelung>
					<artikelart>Arzneimittel</artikelart>
					<mwstsatz>19.00</mwstsatz>
					<listenEk>{int(sale_vk * 0.6)}</listenEk>
					<listenVk>{sale_vk}</listenVk>
					<tatsaechlicherVk>{sale_vk}</tatsaechlicherVk>
					<verkaufsmenge>1</verkaufsmenge>
				</subtotalzeile>
			</subtotal>
		</total>
"""
        xml_content += f"""	</verkaufsblock>
	<wareneingangsblock>
		<wareneingang>
			<beleg>WE-SIM-991</beleg>
			<verarbeitetAm>{now_iso}</verarbeitetAm>
			<belegVom>{now_iso}</belegVom>
			<belegBetrag>{self.goods_receipts_cents}</belegBetrag>
			<wareneingangszeile>
				<pzn>01122334</pzn>
				<name>Großhandelslieferung Sim</name>
				<menge>100</menge>
				<einheit>ST</einheit>
				<ampreisvAmg>0</ampreisvAmg>
				<ampreisvSgb>0</ampreisvSgb>
				<btm>0</btm>
				<abdaWarengruppe>RX</abdaWarengruppe>
				<darreichungsform>FTA</darreichungsform>
				<anbieter>99999</anbieter>
				<lagertemperaturMin>15</lagertemperaturMin>
				<lagertemperaturMax>25</lagertemperaturMax>
				<notfalldepot>0</notfalldepot>
				<abgaberegelung>Verschreibungspflicht</abgaberegelung>
				<artikelart>Arzneimittel</artikelart>
				<mwstsatz>19.00</mwstsatz>
				<listenEk>1200</listenEk>
				<listenVk>2200</listenVk>
				<liefermenge>{self.goods_receipts_packs}</liefermenge>
			</wareneingangszeile>
		</wareneingang>
	</wareneingangsblock>
	<retourenblock>
		<retoure>
			<retourenzeile>
				<retourenerstattung>{self.returns_cents}</retourenerstattung>
			</retourenzeile>
		</retoure>
	</retourenblock>
	<neinverkaufsblock>
		<neinverkauf>
			<neinverkaufszeile>
				<nachfragemenge>{self.missed_sales_packs}</nachfragemenge>
			</neinverkaufszeile>
		</neinverkauf>
	</neinverkaufsblock>
	<lagerblock>
		<lager>
			<StandVom>{now_iso}</StandVom>
			<lagerzeile>
				<pzn>01122334</pzn>
				<name>Standard-Lagerartikel Sim</name>
				<menge>50</menge>
				<einheit>ST</einheit>
				<ampreisvAmg>0</ampreisvAmg>
				<ampreisvSgb>0</ampreisvSgb>
				<btm>0</btm>
				<abdaWarengruppe>RX</abdaWarengruppe>
				<darreichungsform>FTA</darreichungsform>
				<anbieter>99999</anbieter>
				<lagertemperaturMin>15</lagertemperaturMin>
				<lagertemperaturMax>25</lagertemperaturMax>
				<notfalldepot>0</notfalldepot>
				<abgaberegelung>Verschreibungspflicht</abgaberegelung>
				<artikelart>Arzneimittel</artikelart>
				<mwstsatz>19.00</mwstsatz>
				<listenEk>1200</listenEk>
				<listenVk>2200</listenVk>
				<bestand>{self.stock_packs}</bestand>
				<fruehesterVerfall>2026-10-30T00:00:00Z</fruehesterVerfall>
			</lagerzeile>
		</lager>
	</lagerblock>
</adwsroot>
"""
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(xml_content)

    def step(self):
        """Simulates one cycle of live WWKS2 events and ADAS XML updates with lively variations."""
        self.step_counter += 1

        # 1. WWKS2 Status (95% Ready, 5% Busy/NotReady)
        status_val = "Ready" if random.random() > 0.05 else "NotReady"
        self.service.wwks2_tracker.process_wwks2_xml(f'<StatusResponse State="{status_val}" />')

        # 2. Package Outputs (dispensing at POS counters)
        if random.random() > 0.15:  # Frequent dispensing
            # Sine wave output duration (e.g., peak times take slightly longer)
            sine_offset = math.sin(self.step_counter / 5.0) * 3.0
            dur = round(max(4.2, 8.5 + sine_offset + random.uniform(-1.5, 2.5)), 1)
            status = "Completed" if random.random() > 0.03 else "Aborted"
            self.service.wwks2_tracker.process_wwks2_xml(
                f'<OutputMessage Status="{status}" DurationSeconds="{dur}" />'
            )

        # 3. Package Inputs (Stocking replenishment)
        if random.random() > 0.6:
            self.service.wwks2_tracker.process_wwks2_xml('<InputMessage Status="Completed" />')

        # 4. Task Queue Fluctuations (0 to 5 queued, 0 to 3 in-process)
        q_count = random.randint(0, 5)
        p_count = random.randint(0, 2)
        tasks_xml = "".join(['<Task Status="Queued"/>' for _ in range(q_count)])
        tasks_xml += "".join(['<Task Status="InProcess"/>' for _ in range(p_count)])
        self.service.wwks2_tracker.process_wwks2_xml(f'<TaskInfo>{tasks_xml}</TaskInfo>')

        # 5. Daily Sales & Stock Replenishment
        if random.random() > 0.3:
            sales_inc = random.randint(1, 3)
            self.sales_count += sales_inc
            self.items_sold += sales_inc
            self.sales_cents += sales_inc * random.randint(950, 4800)
            self.stock_packs = max(1000, self.stock_packs - sales_inc)

        # 6. Periodic Goods Receipts (every ~10 steps)
        if self.step_counter % 10 == 0:
            self.goods_receipts_count += 1
            delivery_packs = random.randint(15, 60)
            self.goods_receipts_packs += delivery_packs
            self.stock_packs += delivery_packs
            self.goods_receipts_cents += delivery_packs * 1400

        # 7. Occasional Missed Sales (Neinverkäufe)
        if random.random() > 0.8:
            self.missed_sales_count += 1
            self.missed_sales_packs += 1

        # 8. Occasional Returns
        if random.random() > 0.9:
            self.returns_count += 1
            self.returns_cents += random.randint(1200, 4500)

        # 9. Expiration & Old Stock Minor Variation
        self.expiring_90d = max(10, self.expiring_90d + random.choice([-1, 0, 1]))

        # 10. Generate ADAS XML file
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        xml_path = os.path.join(self.inbox_dir, f"ADAS_DAT_1234567_{timestamp_str}.xml")
        self.generate_mock_adas_xml(xml_path)

        # Direct override to ensure all 14 ADAS metrics are published instantly
        self.service.latest_adas_metrics.total_sales_count = self.sales_count
        self.service.latest_adas_metrics.total_sales_amount_cents = self.sales_cents
        self.service.latest_adas_metrics.total_items_sold = self.items_sold
        self.service.latest_adas_metrics.total_stock_packs = self.stock_packs
        self.service.latest_adas_metrics.expiring_90d_count = self.expiring_90d
        self.service.latest_adas_metrics.old_stock_180d_count = self.old_stock_180d
        self.service.latest_adas_metrics.goods_receipts_count = self.goods_receipts_count
        self.service.latest_adas_metrics.goods_receipts_packs = self.goods_receipts_packs
        self.service.latest_adas_metrics.goods_receipts_amount_cents = self.goods_receipts_cents
        self.service.latest_adas_metrics.returns_count = self.returns_count
        self.service.latest_adas_metrics.returns_amount_cents = self.returns_cents
        self.service.latest_adas_metrics.missed_sales_count = self.missed_sales_count
        self.service.latest_adas_metrics.missed_sales_requested_packs = self.missed_sales_packs

        # 11. Run service update cycle
        self.service.update()


def main():
    parser = argparse.ArgumentParser(description="Apotheken Live Simulator (WWKS2 & ADAS-DWS)")
    parser.add_argument("--inbox", default="./inbox", help="Path to ADAS-DWS inbox directory")
    parser.add_argument("--mqtt-host", default="localhost", help="MQTT Broker hostname or IP")
    parser.add_argument("--mqtt-port", type=int, default=1883, help="MQTT Broker port")
    parser.add_argument("--interval", type=int, default=3, help="Simulation loop interval in seconds")
    parser.add_argument("--once", action="store_true", help="Run single pass and exit")
    args = parser.parse_args()

    simulator = PharmacySimulator(inbox_dir=args.inbox, mqtt_host=args.mqtt_host, mqtt_port=args.mqtt_port)
    logger.info(f"Starting Apotheken High-Activity Live Simulator connecting to {args.mqtt_host}:{args.mqtt_port} (Interval: {args.interval}s)...")
    
    if args.once:
        simulator.step()
        logger.info("Simulator single pass completed.")
    else:
        try:
            while True:
                simulator.step()
                time.sleep(args.interval)
        except KeyboardInterrupt:
            logger.info("Simulator stopped.")


if __name__ == "__main__":
    main()
