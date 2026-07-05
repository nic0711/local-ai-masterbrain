# 23 · Monitoring (Prometheus-Stack)

## Überblick

Der optionale Monitoring-Stack besteht aus vier Services mit dem Compose-Profil `monitoring`:

| Service | Container | Port (intern) | Zweck |
|---|---|---|---|
| Prometheus | `prometheus` | 9090 | Metriken-Datenbank + Scraper |
| Node Exporter | `node-exporter` | 9100 | Host-Metriken (CPU, RAM, Disk, Netz) |
| cAdvisor | `cadvisor` | 8080 | Docker-Container-Metriken |
| Pushgateway | `pushgateway` | 9091 | Empfängt Push-Metriken (n8n, SPS, Solar) |

Grafana ist bereits im Kern-Stack enthalten. Die Prometheus-Datasource wird automatisch via Provisioning konfiguriert.

## Starten

```bash
# Kompletter Stack mit Monitoring
docker compose --profile cpu --profile monitoring up -d

# Nur Monitoring-Stack (Grafana läuft bereits)
docker compose --profile monitoring up -d

# Einzeln via Dashboard-Macro
# → Dashboard → Macros → "Monitoring starten"
```

## Stoppen

```bash
docker compose --profile monitoring down

# oder via Dashboard: "Monitoring stoppen"
```

## Konfiguration

### Prometheus-Scrape-Targets (`prometheus/prometheus.yml`)

```yaml
scrape_configs:
  - job_name: "node-exporter"    # Host-Metriken
  - job_name: "cadvisor"         # Container-Metriken
  - job_name: "pushgateway"      # Externe Push-Metriken
```

Datei wird per Volume in den Container gemountet. Nach Änderungen:

```bash
docker compose exec prometheus kill -HUP 1
```

### Grafana-Datasource (automatisch)

`grafana/provisioning/datasources/prometheus.yml` wird beim Grafana-Start automatisch geladen.
Datasource-Name: `Prometheus` (als Default markiert).

### Dashboard-Vorlagen

Dashboards in `grafana/dashboards/` werden automatisch geladen (Provider `localai`).
Empfohlene Community-Dashboards:
- Node Exporter Full: ID `1860`
- Docker Container: ID `893`

Import via Grafana UI: Dashboards → Import → Grafana.com ID eingeben.

## Daten-Retention

Prometheus speichert Metriken standardmäßig **30 Tage** (`--storage.tsdb.retention.time=30d`).
Daten liegen im Volume `prometheus_data`.

```bash
# Disk-Verbrauch prüfen
docker exec prometheus df -h /prometheus
```

## Pushgateway (für n8n-Workflows)

n8n-Workflows können Metriken an den Pushgateway senden:

```bash
# Beispiel: Solar-Ertrag pushen
curl -X POST http://pushgateway:9091/metrics/job/solar \
  -H "Content-Type: text/plain" \
  --data-binary "solar_power_watts 1250.5\n"
```

Im n8n-Workflow: HTTP-Node → `http://pushgateway:9091/metrics/job/<jobname>` (POST, text/plain).

## Zugriff

Prometheus ist nicht über Caddy exponiert (nur intern). Zugriff über Grafana oder direkt via SSH-Tunnel:

```bash
# SSH-Tunnel für direkten Prometheus-Zugriff
ssh -L 9090:localhost:9090 user@brain.local
# dann: http://localhost:9090
```

## Troubleshooting

**Prometheus startet nicht:**
```bash
docker compose logs prometheus
# Häufig: Syntaxfehler in prometheus/prometheus.yml
docker run --rm -v $(pwd)/prometheus:/prometheus prom/prometheus:latest --check-config
```

**cAdvisor benötigt privilegierten Modus:**
cAdvisor läuft mit `privileged: true` und `/dev/kmsg` – das ist für Container-Metriken erforderlich und bekannt.

**Grafana zeigt keine Daten:**
1. Datasource prüfen: Grafana → Configuration → Data Sources → Prometheus → Test
2. Prometheus-Targets prüfen: `http://localhost:9090/targets` (via Tunnel)
3. Zeitraum im Dashboard anpassen (letzte 5 min, nicht 24h bei frischem Start)
