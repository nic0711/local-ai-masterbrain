# 24 · SPS-Monitoring (OPC-UA, MQTT, Modbus)

## Überblick

Drei Protokoll-Exporter für SPS/PLC-Metriken, alle mit Compose-Profil `monitoring`:

| Protokoll | Container | Port | Exporter |
|---|---|---|---|
| MQTT | `mqtt2prometheus` | 9641 | [hikhvar/mqtt2prometheus](https://github.com/hikhvar/mqtt2prometheus) |
| Modbus TCP | `modbus-exporter` | 9602 | [nmaarse/modbus_exporter](https://github.com/nmaarse/modbus_exporter) |
| OPC-UA | – (Grafana-Plugin) | – | grafana-opcua-datasource |

Alle Exporter scrapen Prometheus. Grafana visualisiert die Daten.

## Starten

```bash
# Zusammen mit dem vollen Monitoring-Stack
docker compose --profile monitoring up -d

# Nur SPS-Exporter (wenn Prometheus bereits läuft)
docker compose --profile monitoring up -d mqtt2prometheus modbus-exporter

# Via Dashboard-Macro: "SPS-Monitoring starten"
```

## MQTT-Monitoring (mqtt2prometheus)

### Konfiguration

`sps-monitoring/mqtt2prometheus.yml` anpassen:
- `SPS_MQTT_BROKER` in `.env` setzen (z.B. `tcp://192.168.1.10:1883`)
- MQTT-Topics und Prometheus-Metriken-Namen anpassen

```yaml
metrics:
  - prom_name: sps_temperature_celsius
    mqtt_name: sps/temperature    # MQTT-Topic
    type: gauge
```

### Voraussetzung
Ein MQTT-Broker muss erreichbar sein (z.B. Mosquitto, EMQX, oder direkt auf der SPS).
Wenn kein eigener Broker vorhanden: Mosquitto kann als weiterer optionaler Service hinzugefügt werden.

### Grafana-Dashboard
Nach dem Start: Dashboards → Import → Community-Dashboard-ID `11074` (MQTT Overview) oder eigenes Dashboard mit dem `mqtt2prometheus`-Job.

## Modbus-Monitoring (modbus-exporter)

### Konfiguration

1. `SPS_MODBUS_HOST` und `SPS_MODBUS_PORT` in `.env` setzen
2. `sps-monitoring/modbus.yml` anpassen:

```yaml
modules:
  plc_main:
    address: "${SPS_MODBUS_HOST}:${SPS_MODBUS_PORT}"
    registers:
      - name: temperature_raw
        address: 0x0001
        data_type: int16
        factor: 0.1
```

Register-Adressen aus der SPS-Dokumentation (Holding Registers, Coils, Input Registers).

### Grafana-Dashboard
Dashboards → Import → eigenes Dashboard mit Job `modbus-exporter` oder Metriken direkt in der Query nutzen (z.B. `modbus_temperature_raw`).

## OPC-UA-Monitoring (Grafana-Plugin)

OPC-UA wird als **direkte Grafana-Datasource** ohne separaten Container implementiert.

### Setup

1. `.env` setzen:
   ```bash
   GF_INSTALL_PLUGINS=grafana-opcua-datasource
   GRAFANA_OPCUA_ENDPOINT=opc.tcp://plc:4840
   ```

2. Grafana-Datasource-Template aktivieren:
   ```bash
   cp grafana/provisioning/datasources/opcua.yml.template \
      grafana/provisioning/datasources/opcua.yml
   ```

3. Grafana neustarten:
   ```bash
   docker compose restart grafana
   # oder via Dashboard-Control
   ```

4. Grafana → Configuration → Data Sources → "OPC-UA SPS" erscheint automatisch.

### Sicherheit

OPC-UA unterstützt verschiedene Sicherheitsrichtlinien (`securityPolicy` in `opcua.yml`):
- `None`: Unverschlüsselt (nur im isolierten Netz)
- `Basic256Sha256`: Empfohlen für produktive Umgebungen

Zertifikate werden im Grafana-Datenpfad gespeichert.

## Prometheus-Scrape-Targets

Alle drei Exporter sind in `prometheus/prometheus.yml` konfiguriert:

```yaml
- job_name: "mqtt2prometheus"
  static_configs:
    - targets: ["mqtt2prometheus:9641"]

- job_name: "modbus-exporter"
  static_configs:
    - targets: ["modbus-exporter:9602"]
```

Prometheus-Targets-Status: `http://localhost:9090/targets` (via SSH-Tunnel).

## Troubleshooting

**mqtt2prometheus verbindet sich nicht:**
```bash
docker compose logs mqtt2prometheus
# Broker-Adresse und Port in .env prüfen
# Test: mosquitto_pub -h <broker> -t sps/test -m "42"
```

**modbus-exporter: Timeout:**
```bash
docker compose logs modbus-exporter
# SPS-IP, Port (502) und Unit-ID in sps-monitoring/modbus.yml prüfen
# Firewall: SPS muss TCP/502 akzeptieren
```

**OPC-UA-Plugin fehlt in Grafana:**
```bash
# Plugin-Installation prüfen
docker exec grafana grafana-cli plugins ls | grep opcua
# Bei Fehler: Grafana neustarten
docker compose restart grafana
```
