# 27 · Wissensdatenbank (KB-Workflows)

## Überblick

Drei Ingest-Workflows befüllen Neo4j und Qdrant aus verschiedenen Quellen:

| Workflow | Datei | Quelle | Trigger |
|---|---|---|---|
| PDF-Ingest | `kb-pdf-ingest.json` | PDF/Dokument (URL oder Text) | Webhook POST |
| Web-Research | `kb-web-research.json` | Crawl4AI, beliebiger Webhook-Sender | Webhook POST |
| osTicket KB | `osticket-to-knowledge-base.json` | Gelöste Tickets | täglich 02:00 |

Alle Workflows schreiben in:
- **Qdrant** `knowledge_base` (Vektorsuche, Dim 768, Cosine)
- **Neo4j** via `python-nlp-service /graph/index` (Graph, NER-Entitäten)

---

## Setup

### 1. Qdrant-Collections anlegen

```bash
# knowledge_base Collection (PDF + Research)
bash scripts/init_qdrant_kb.sh

# osticket_solutions Collection (falls noch nicht aus Schritt 9)
bash scripts/init_qdrant_osticket.sh
```

### 2. Neo4j initialisieren

```bash
# Schema + Constraints anlegen (einmalig)
curl -X POST http://python-nlp-service:5000/graph/init
```

### 3. n8n Variable setzen

| Variable | Wert | Verwendet in |
|---|---|---|
| `KB_INGEST_API_KEY` | Zufälliger langer String | kb-pdf-ingest, kb-web-research |

```bash
# Beispiel: sicherer Key generieren
openssl rand -hex 32
```

Setzen: n8n → Settings → Variables → `KB_INGEST_API_KEY`

### 4. Workflows importieren

```
n8n → Import:
  n8n-tool-workflows/kb-pdf-ingest.json
  n8n-tool-workflows/kb-web-research.json
```

Aktivieren. Webhook-URLs erscheinen in n8n unter dem Webhook-Node.

---

## PDF/Dokument indexieren (`kb-pdf-ingest`)

### Webhook

```
POST https://n8n.brain.local/webhook/kb-ingest-pdf
Header: x-kb-api-key: <KB_INGEST_API_KEY>
Content-Type: application/json
```

### Payload: direkt als Text

```json
{
  "doc_id": "handbuch-vpn-2026",
  "title": "VPN-Konfigurationshandbuch",
  "source": "internal_doc",
  "text": "Volltext des Dokuments hier..."
}
```

### Payload: per interner URL (PDF auf MinIO)

```json
{
  "doc_id": "handbuch-vpn-2026",
  "title": "VPN-Konfigurationshandbuch",
  "source": "minio",
  "file_url": "http://minio:9000/documents/handbuch-vpn.pdf"
}
```

`file_url` ist auf interne Hosts beschränkt (`python-nlp-service`, `minio`, `host.docker.internal`) – kein SSRF möglich.

### Verarbeitungsablauf

```
Webhook → Validierung (Auth + SSRF-Check)
  → [falls file_url] PDF-Extraktion via python-nlp-service /pdf/extract
  → NLP-Analyse /document/analyze (NER-Entitäten)
  → Ollama Embedding (nomic-embed-text)
  → Qdrant upsert + Neo4j indexieren (parallel)
```

---

## Web-Research indexieren (`kb-web-research`)

### Webhook

```
POST https://n8n.brain.local/webhook/kb-ingest-research
Header: x-kb-api-key: <KB_INGEST_API_KEY>
Content-Type: application/json
```

### Payload

```json
{
  "title": "Kubernetes Netzwerkmodell – Deep Research",
  "content": "Volltext des Research-Ergebnisses...",
  "source_url": "https://kubernetes.io/docs/...",
  "tags": ["kubernetes", "netzwerk", "devops"]
}
```

### Verarbeitungsablauf

```
Webhook → Validierung
  → NLP-Analyse + Zusammenfassung (Ollama) + Embedding (parallel)
  → Payload bauen
  → Qdrant upsert + Neo4j indexieren (parallel)
```

---

## Wissensdatenbank abfragen

### Qdrant (Ähnlichkeitssuche)

```bash
# Erst Embedding erzeugen
curl -X POST http://host.docker.internal:11434/api/embeddings \
  -d '{"model":"nomic-embed-text","prompt":"VPN funktioniert nicht"}' | jq .embedding > vec.json

# Ähnlichkeitssuche
curl -X POST https://qdrant.brain.local/collections/knowledge_base/points/search \
  -H "Content-Type: application/json" \
  -d "{\"vector\": $(cat vec.json), \"limit\": 5, \"with_payload\": true}"
```

### Neo4j (Graph-Abfrage)

```cypher
-- Alle Dokumente zu einem Begriff
MATCH (d:Document)-[:MENTIONS]->(e:Entity)
WHERE e.name CONTAINS 'VPN'
RETURN d.title, d.source, collect(e.name) AS entities
LIMIT 20
```

### n8n Graph-Query-Endpoint

```bash
curl -X POST http://python-nlp-service:5000/graph/query \
  -H "Content-Type: application/json" \
  -d '{"query": "VPN Konfiguration", "limit": 5}'
```

---

## Troubleshooting

**Qdrant 404 bei upsert:**
```bash
bash scripts/init_qdrant_kb.sh
```

**Embedding-Fehler (Ollama):**
```bash
# Modell prüfen
curl http://host.docker.internal:11434/api/tags | jq '.models[].name'
# Falls nomic-embed-text fehlt:
ollama pull nomic-embed-text
```

**Neo4j-Indexierung schlägt fehl:**
```bash
# python-nlp-service läuft?
docker compose ps python-nlp-service
# Neo4j-Schema initialisieren
curl -X POST http://python-nlp-service:5000/graph/init
```
