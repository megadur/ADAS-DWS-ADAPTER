# ADAS-DWS & WWKS2 Home Assistant Adapter

Ein entkoppelter, lesender Integrations-Adapter zur Einbindung von Apothekendaten (Kommissionierautomat & Warenwirtschaft) in Home Assistant via **MQTT Auto-Discovery**.

## 🌟 Funktionsumfang

1. **WWKS2 Live-Telemetrie (Kommissionierautomat):**
   - Online-Status (`binary_sensor.ks_online`)
   - Automaten-Zustand (`sensor.ks_state`: `Ready`, `NotReady`, `Maintenance`, `Offline`)
   - Aktive Aufträge in der Queue (`sensor.ks_active_tasks`)
   - Auslagerungs- & Einlagerungszähler des Tages (`outputs_today`, `inputs_today`)
   - Rollierende Auslagerungsdauer (`avg_output_time_s_1h`)
   - Rollierende 24h-Fehlerquote in % (`error_rate_24h_pct`)

2. **ADAS-DWS Daten-Import (Warenwirtschaft):**
   - Einlesen und Parsing von ADAS-DWS XML-Dateien (Ausbaustufe 1, 2 und 3)
   - Strenge Datenschutz-Filterung (keine Speicherung/Übertragung von PII, Verkäufer- oder Kundendetails)
   - Aggregierte Tagesstatistiken für Home Assistant (`total_sales_count`, `total_stock_packs`, `expiring_90d_count`, `goods_receipts_count`)

3. **Home Assistant MQTT Auto-Discovery:**
   - Automatische Erkennung und Einrichtung aller Entitäten in Home Assistant ohne manuelle YAML-Edits.

---

## 📁 Verzeichnisstruktur

```
├── ADAS-DWS/                  # Original ADAS-DWS XSD Schema-Definitionen
├── pharmacy_bridge/           # Python Adapter-Paket
│   ├── adas_parser.py         # ADAS XML Parser & Datenschutz-Aggregator
│   ├── wwks2_bridge.py        # WWKS2 Telemetrie & State Machine
│   ├── mqtt_publisher.py      # HA MQTT Discovery & Payload Generator
│   └── service.py             # Hauptdienst Daemon
├── samples/                   # Beispiel-XML-Dateien für Tests
├── tests/                     # Automated Test Suite
├── ha_configuration.yaml      # Home Assistant YAML-Referenz
└── README.md                  # Dokumentation
```

---

## 🚀 Schnellstart

### 1. Vorbereitungen
Der Adapter benötigt Python 3.10+.

### 2. Tests ausführen
```bash
python -m unittest discover -s tests -p "test_*.py"
```

### 3. Einzelnen Test-Durchlauf starten
```bash
python -m pharmacy_bridge.service --inbox ./inbox --once
```

### 4. Service im Hintergrund ausführen
```bash
python -m pharmacy_bridge.service --inbox ./inbox --mqtt-host 127.0.0.1 --mqtt-port 1883
```

Sobald der Service läuft und XML-Dateien in den Ordner `./inbox` gelegt werden, liest der Adapter diese automatisch ein und sendet die aggregierten Kennzahlen an den MQTT-Broker. Home Assistant erkennt die neuen Sensoren automatisch.

---

## 🔒 Datenschutz & Sicherheit

- Der Adapter liest Daten ausschließlich im **Passiv-/Read-only-Modus**.
- Es werden **keine Schreib- oder Steuerbefehle** an Kommissionierer oder Warenwirtschaft gesendet.
- Sensible Felder wie `verkaeufer` und `verbraucher` werden beim Parsing strikt verworfen.
