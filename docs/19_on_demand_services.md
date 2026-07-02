# 19. On-Demand Service Control

Ressourcenintensive Services starten beim Stack-Boot nicht automatisch. Sie können per Dashboard-Admin-Tab oder n8n-Toolcall auf Abruf gestartet und wieder gestoppt werden.

---

## Optionale Services

| Service | Funktion | Warum optional |
|---|---|---|
| `neo4j` | Knowledge Graph | RAM-intensiv, nur für RAG-Workflows |
| `flowise` | AI Agent Builder | Selten täglich genutzt |
| `minio` | S3-Objektspeicher | Nur für Langfuse-Traces nötig |
| `clickhouse` | Analytics-DB | Nur für Langfuse-Traces nötig |
| `langfuse-web` | LLM Observability UI | Nur beim Debugging |
| `langfuse-worker` | Trace-Verarbeitung | Abhängig von minio + clickhouse |

**Immer laufend:** `n8n`, `open-webui`, `qdrant`, `searxng`, `crawl4ai`, `python-nlp-service`, `uptime-kuma`, `grafana`, `postgres`, `redis` (Basisinfrastruktur).

---

## Technische Umsetzung

### Docker Compose Profile

Die 6 optionalen Services haben `profiles: [optional]` in `docker-compose.yml`. Dadurch werden sie bei `docker compose up -d` (ohne `--profile optional`) übersprungen.

`start_services.py --profile none` übergibt kein `--profile optional` → optionale Services bleiben gestoppt.

### auth-gateway: Zwei-Wege-Start

Wenn ein optionaler Service gestartet werden soll:

1. **Container existiert** (gestoppt): Docker SDK → `container.start()`
2. **Container fehlt** (erster Start): `docker compose --profile optional up -d <service>`

Der subprocess-Aufruf im auth-gateway verwendet `HOST_PROJECT_DIR` (per Env-Var vom Host übergeben), damit die Volume-Pfade korrekt auf Host-Pfade zeigen statt auf Container-interne Pfade.

### Volume-Pfade

Neo4j-Volumes nutzen `${HOST_PROJECT_DIR:-.}/neo4j/...` statt `./ neo4j/...`, damit der Docker-Daemon (der Host-Pfade verlangt) die richtigen Pfade erhält wenn compose aus dem Container aufgerufen wird.

Flowise nutzt ein **named volume** (`flowise:/root/.flowise` statt `~/.flowise:/root/.flowise`), da `~` im Container-Kontext auf das Container-Home zeigt, nicht auf das Host-Home.

---

## Control-Interfaces

### 1. Dashboard (Admin-Tab)

Im Dashboard unter `https://brain.local` → Admin-Tab gibt es ein Service-Control-Panel mit:
- Status-Anzeige (grün = running, grau = stopped/absent)
- Start/Stop-Buttons pro Service
- Macro-Buttons für häufige Kombinationen

### 2. auth-gateway REST API

```bash
TOKEN=<jwt>

# Status aller Services
curl https://brain.local/_control/services/status -H "Authorization: Bearer $TOKEN"

# Einzelnen Service starten
curl -X POST https://brain.local/_control/services/neo4j/start \
  -H "Authorization: Bearer $TOKEN"

# Macro ausführen
curl -X POST https://brain.local/_control/macro/langfuse-start \
  -H "Authorization: Bearer $TOKEN"
```

### 3. n8n-Toolcall (KI-Agent)

Workflow: `n8n-tool-workflows/stack-service-control.json`

```bash
curl -X POST https://n8n.brain.local/webhook/service-control \
  -H "Content-Type: application/json" \
  -H "Cookie: sb-access-token=$TOKEN" \
  -d '{"service": "neo4j", "action": "start"}'
```

**n8n-Credential anlegen:** HTTP Header Auth mit Name `Auth Gateway JWT`, Header `Authorization: Bearer <langlebiger JWT>`.

---

## Macros

Definiert in `dashboard/macros.json`:

| ID | Label | Aktionen |
|---|---|---|
| `light-mode` | Leicht-Modus | Open WebUI + n8n starten, optionale stoppen |
| `research` | Research-Modus | SearXNG + Crawl4AI + Open WebUI + n8n |
| `rag-mode` | RAG-Modus | Qdrant + Neo4j + NLP + Open WebUI + n8n |
| `langfuse-start` | Langfuse starten | MinIO + ClickHouse + Langfuse-Web + Worker |
| `save-resources` | Ressourcen sparen | Alle optionalen Services stoppen |
| `restart-core` | Core neustarten | n8n + Open WebUI + Flowise neu starten |

**Stop-Verhalten:** Wenn ein Container bei einem Stop-Befehl nicht gefunden wird (schon gestoppt/nie gestartet), gilt dies als Erfolg — kein Fehler.

---

## Erster Start eines optionalen Service

Beim allerersten Start (Container existiert noch nicht) wird `docker compose --profile optional up -d <service>` aufgerufen. Dies:
- Lädt das Image (falls nicht gecacht) — kann einige Minuten dauern
- Erstellt den Container mit korrekter Konfiguration
- Startet ihn

Bei `langfuse-web` werden automatisch `minio`, `clickhouse` und `langfuse-worker` mitgestartet (`depends_on` in compose).

---

## Hinweise für Stack-Neustart

Nach `start_services.py --profile none` sind alle optionalen Services gestoppt (Container existieren aber noch). Beim nächsten Start via Dashboard/API → Container.start() (kein compose-Overhead, schnell).

Nach `docker compose down` oder `docker rm` der Container → nächster Start läuft wieder über compose (langsamer, sauber).
