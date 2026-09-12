"""
Apotheken Simulator & Mock Data Generator
Simulates both:
1. WWKS2 live events (Hello, KeepAlive, OutputMessage, TaskInfo, StatusResponse)
2. ADAS-DWS XML export file generation (Verkäufe, Wareneingang, Lagerbestand, Verfallsdaten)

Generates dynamic, live-updating metrics for Home Assistant dashboards.
"""

import argparse
from datetime import datetime, timezone
import logging
import os
import random
import time

try:
    from .wwks2_bridge import WWKS2TelemetryTracker
    from .adas_parser import parse_adas_xml
    from .service import PharmacyAdapterService
except ImportError:
    from pharmacy_bridge.wwks2_bridge import WWKS2TelemetryTracker
    from pharmacy_bridge.adas_parser import parse_adas_xml
    from pharmacy_bridge.service import PharmacyAdapterService

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("pharmacy_simulator")


def generate_mock_adas_xml(filepath: str, sales_count: int = 15, total_cents: int = 24500, stock_packs: int = 18450, btm_nr: str = "1234567"):
    """Generates a realistic ADAS-DWS v1.0 Ausbaustufe 2 XML file with simulated daily pharmacy metrics."""
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<adwsroot xmlns="http://www.adas.de/spec/dws/v1">
	<kopf>
		<version>1.0</version>
		<absender>BGANr{btm_nr}</absender>
		<erstelltAm>{now_iso}</erstelltAm>
		<instanzId>Server-Sim</instanzId>
		<system>
			<anbieter>PHARMATECHNIK</anbieter>
			<systembezeichnung>IXOS (Simuliert)</systembezeichnung>
		</system>
	</kopf>
	<verkaufsblock>
"""
    for i in range(sales_count):
        sale_vk = total_cents // sales_count if sales_count > 0 else 1250
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
			<belegBetrag>14500</belegBetrag>
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
				<liefermenge>45</liefermenge>
			</wareneingangszeile>
		</wareneingang>
	</wareneingangsblock>
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
				<bestand>{stock_packs}</bestand>
				<fruehesterVerfall>2026-10-30T00:00:00Z</fruehesterVerfall>
			</lagerzeile>
		</lager>
	</lagerblock>
</adwsroot>
"""
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(xml_content)
    logger.info(f"Generated ADAS XML: {sales_count} sales, {stock_packs} stock packs")


class PharmacySimulator:
    def __init__(self, inbox_dir: str = "./inbox", mqtt_host: str = "localhost", mqtt_port: int = 1883, node_id: str = "ks01"):
        self.inbox_dir = inbox_dir
        self.node_id = node_id
        self.service = PharmacyAdapterService(inbox_dir=inbox_dir, mqtt_host=mqtt_host, mqtt_port=mqtt_port, node_id=node_id)
        
        # Live simulation counters
        self.sales_count = 145
        self.sales_cents = 284500
        self.stock_packs = 18450
        
        # Initialize WWKS2 with Hello
        self.service.wwks2_tracker.process_wwks2_xml(
            '<Hello Manufacturer="BD Rowa (Simulated)" Product="Vmax" Version="2.4.1" />'
        )

    def step(self):
        """Simulates one cycle of live WWKS2 events and ADAS XML updates."""
        # 1. Simulate WWKS2 Status (95% Ready, 5% NotReady)
        status_val = "Ready" if random.random() > 0.05 else "NotReady"
        self.service.wwks2_tracker.process_wwks2_xml(f'<StatusResponse State="{status_val}" />')
        
        # 2. Simulate Package Output dispensing
        if random.random() > 0.2:
            dur = round(random.uniform(4.5, 16.5), 1)
            status = "Completed" if random.random() > 0.03 else "Aborted"
            self.service.wwks2_tracker.process_wwks2_xml(
                f'<OutputMessage Status="{status}" DurationSeconds="{dur}" />'
            )
            
        # 3. Simulate Dynamic Task Queue (varying between 0 and 6 tasks)
        q_count = random.randint(0, 4)
        p_count = random.randint(0, 2)
        tasks_xml = "".join(['<Task Status="Queued"/>' for _ in range(q_count)])
        tasks_xml += "".join(['<Task Status="InProcess"/>' for _ in range(p_count)])
        self.service.wwks2_tracker.process_wwks2_xml(f'<TaskInfo>{tasks_xml}</TaskInfo>')

        # 4. Increment simulated daily sales and decrease stock
        if random.random() > 0.4:
            new_sales = random.randint(1, 3)
            self.sales_count += new_sales
            self.sales_cents += new_sales * random.randint(800, 3200)
            self.stock_packs = max(1000, self.stock_packs - new_sales)

        # 5. Periodically write ADAS XML export file
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        xml_path = os.path.join(self.inbox_dir, f"ADAS_DAT_1234567_{timestamp_str}.xml")
        generate_mock_adas_xml(xml_path, sales_count=self.sales_count, total_cents=self.sales_cents, stock_packs=self.stock_packs)

        # 6. Service update cycle (processes inbox and publishes MQTT states)
        self.service.update()


def main():
    parser = argparse.ArgumentParser(description="Apotheken Simulator (WWKS2 & ADAS-DWS)")
    parser.add_argument("--inbox", default="./inbox", help="Path to ADAS-DWS inbox directory")
    parser.add_argument("--mqtt-host", default="localhost", help="MQTT Broker hostname or IP")
    parser.add_argument("--mqtt-port", type=int, default=1883, help="MQTT Broker port")
    parser.add_argument("--interval", type=int, default=5, help="Simulation loop interval in seconds")
    parser.add_argument("--once", action="store_true", help="Run single pass and exit")
    args = parser.parse_args()

    simulator = PharmacySimulator(inbox_dir=args.inbox, mqtt_host=args.mqtt_host, mqtt_port=args.mqtt_port)
    logger.info(f"Starting Apotheken Live Simulator connecting to {args.mqtt_host}:{args.mqtt_port} (Interval: {args.interval}s)...")
    
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
