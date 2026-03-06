# 10. Python NLP / Document Service

Der `python-nlp-service` ist der zentrale Dokumentenverarbeitungs-Container im Stack. Er bietet:

- **OCR** – Texterkennung aus Bildern und gescannten PDFs via Ollama (`glm-ocr`)
- **PDF-Extraktion** – direkter Text aus digitalen PDFs (PyMuPDF), mit automatischem OCR-Fallback
- **NER** – Named Entity Recognition auf Deutsch und Englisch (SpaCy)
- **Kombinierter Endpoint** – `/document/analyze` liefert Text + Entities in einem Call

---

## Konfiguration

| Env-Variable | Default | Beschreibung |
|---|---|---|
| `OLLAMA_HOST` | `http://host.docker.internal:11434` | Ollama-Endpunkt für OCR. Auf dem Server: `http://ollama:11434` |
| `OCR_MODEL` | `glm-ocr` | Ollama-Modell für OCR. Vorab pullen: `ollama pull glm-ocr` |
| `WORKERS` | `2` | Gunicorn Worker-Prozesse |
| `THREADS` | `4` | Gunicorn Threads pro Worker |
| `TIMEOUT` | `120` | Request-Timeout in Sekunden (OCR kann dauern) |

In `.env` überschreibbar (Standardwerte funktionieren auf dem Mac ohne Änderung):

```bash
# Server-Betrieb mit Ollama im Container:
OLLAMA_HOST=http://ollama:11434

# Anderes OCR-Modell:
OCR_MODEL=llama3.2-vision:11b
```

---

## OCR-Modell pullen

Bevor OCR genutzt werden kann, muss das Modell in Ollama verfügbar sein:

```bash
# Auf dem Mac (Ollama läuft lokal):
ollama pull glm-ocr

# Im laufenden Stack auf dem Server:
docker exec ollama ollama pull glm-ocr
```

---

## API-Referenz

### `GET /health`
Docker-Health-Check. Gibt `200 healthy` zurück, wenn alle SpaCy-Modelle geladen sind.

### `GET /status`
Detaillierter Status: geladene Modelle, verfügbare Endpoints, Ollama-Konfiguration.

---

### `POST /document/analyze` ⭐ Haupt-Endpoint

Universeller Endpoint für Dokumente – gibt Text **und** Entities in einem Call zurück. Ideal für n8n-Workflows und Neo4j-Pipelines.

**Input:** `multipart/form-data`

| Feld | Typ | Beschreibung |
|---|---|---|
| `file` | PDF oder Bild | Zu verarbeitendes Dokument |
| `lang` | `de` \| `en` | Sprache für NER (default: `de`) |

Alternativ: JSON-Body `{"text": "...", "lang": "de"}` für reinen Text.

**Response:**
```json
{
  "text": "Extrahierter Volltext des Dokuments...",
  "entities": [
    {"text": "Mustermann GmbH", "label": "ORG", "start": 12, "end": 27},
    {"text": "01.03.2026",      "label": "DATE", "start": 45, "end": 55},
    {"text": "Berlin",          "label": "LOC", "start": 60, "end": 66}
  ],
  "entity_count": 3,
  "needs_ocr": false,
  "language": "de"
}
```

**Beispiel n8n HTTP-Request-Node:**
```
Method: POST
URL:    http://python-nlp-service:5000/document/analyze
Body:   Form-Data
  file: {{ $binary.data }}
  lang: de
```

---

### `POST /process`

Nur NER – kein Dokument, nur Text. Für bestehende Workflows.

**Input:** JSON
```json
{"text": "Angela Merkel war in Berlin.", "lang": "de"}
```

**Response:**
```json
{
  "original_text": "Angela Merkel war in Berlin.",
  "processed": true,
  "length": 28,
  "language": "de",
  "entities": [
    {"text": "Angela Merkel", "label": "PER", "start": 0,  "end": 13},
    {"text": "Berlin",        "label": "LOC", "start": 22, "end": 28}
  ]
}
```

---

### `POST /pdf/extract`

PDF → Text (direkt oder via OCR).

**Input:** `multipart/form-data`, Feld: `file`

**Response:**
```json
{
  "text": "Volltext des PDFs...",
  "needs_ocr": false,
  "page_count": 3
}
```

---

### `POST /pdf/analyze-type`

Erkennt, ob ein PDF Text-basiert oder gescannt ist. Kompatibilität mit bestehendem n8n-Workflow.

**Input:** `multipart/form-data`, Feld: `file`

**Response:**
```json
{
  "extracted_text": "...",
  "needs_ocr": true,
  "page_count": 2
}
```

---

### `POST /pdf/to-png-smart`

Konvertiert PDF-Seiten zu PNG (base64). Kompatibilität mit bestehendem n8n-Workflow.

**Input:** `multipart/form-data`, Feld: `file`

**Response:**
```json
{
  "pages": [
    {"page": 1, "image_base64": "iVBORw0KGgo..."},
    {"page": 2, "image_base64": "iVBORw0KGgo..."}
  ],
  "page_count": 2
}
```

---

## Einsatz mit Neo4j

Der `/document/analyze`-Endpoint liefert direkt die Rohdaten für einen Knowledge Graph:

```
Rechnung (PDF) → /document/analyze
  → text:     Volltext für LLM-Extraktion
  → entities: [Mustermann GmbH (ORG), Berlin (LOC), 01.03.2026 (DATE)]
    → Neo4j Nodes: (:Organization), (:Location), (:Date)
    → Neo4j Relationships: (:Invoice)-[:ISSUED_BY]->(:Organization)
```

Ein n8n-Workflow kann die Entities direkt per Cypher-Query in Neo4j schreiben:

```cypher
MERGE (o:Organization {name: $name})
MERGE (i:Invoice {id: $invoiceId})
MERGE (i)-[:ISSUED_BY]->(o)
```

---

## Ressourcen

| Ressource | Wert |
|---|---|
| RAM-Limit | 1.5 GB |
| RAM-Reservation | 768 MB |
| Port | 5000 (intern, nicht nach außen exposed) |
| SpaCy DE-Modell | `de_core_news_md` (~43 MB) |
| SpaCy EN-Modell | `en_core_web_md` (~43 MB) |
| Max. Dateigröße | 50 MB |
| Max. Textlänge | 50.000 Zeichen |
