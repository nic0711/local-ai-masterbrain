# 14. OCR Service

Der `ocr-service` ist ein eigenständiger FastAPI-Container mit hybrider OCR-Pipeline.
Er kombiniert Microsoft TrOCR (transformerbasiert) und Tesseract (klassisch) mit automatischer Engine-Auswahl.

---

## Architektur

```
n8n / Dashboard
    │
    ▼
ocr-service:8002  (FastAPI, Python 3.11)
    ├── TrOCR Engine      – Microsoft/trocr-large-printed  (Hugging Face)
    ├── Tesseract Engine  – tesseract-ocr (apt, v5)
    └── Auto Mode         – wählt Engine basierend auf Bildqualität
    │
    ▼
/data/input   – Eingabedateien (mounted: ocr_storage/input)
/data/output  – Ergebnisse     (mounted: ocr_storage/output)
/data/temp    – Zwischendateien (mounted: ocr_storage/temp)
```

---

## Setup

### 1. docker-compose.yml

Der Service ist im Hauptstack bereits definiert:

```yaml
ocr-service:
  build: ./ocr-service
  container_name: ocr-service
  ports:
    - "8002:8002"
  volumes:
    - ./ocr_storage:/data
  environment:
    - OCR_DEFAULT_ENGINE=${OCR_DEFAULT_ENGINE:-auto}
    - OCR_LANGUAGE=${OCR_LANGUAGE:-en}
  restart: unless-stopped
```

### 2. Caddy-Route (caddy-addon/ocr.conf)

```caddy
ocr.{$DOMAIN} {
  import forward_auth
  reverse_proxy ocr-service:8002
}
```

Damit ist der Service unter `https://ocr.brain.local` erreichbar (hinter Auth).

### 3. Umgebungsvariablen (.env)

```bash
OCR_DEFAULT_ENGINE=auto     # auto | trocr | tesseract
OCR_LANGUAGE=en             # ISO-639-1 Sprachcode für Tesseract
```

---

## Endpunkte

### GET `/`
Root health check.

**Response:**
```json
{ "status": "healthy", "service": "trocr", "version": "2.0.0" }
```

---

### GET `/health`
Detaillierter Health-Check: Engine-Status, Verzeichnisse.

**Response:**
```json
{
  "status": "healthy",
  "engines": { "trocr": "loaded", "tesseract": "available" },
  "available_engines": ["trocr", "tesseract"],
  "temp_dir": true,
  "input_dir": true,
  "output_dir": true
}
```

---

### GET `/engines`
Listet verfügbare OCR-Engines.

**Response:**
```json
{
  "engines": [
    { "name": "trocr",     "status": "loaded",    "model": "microsoft/trocr-large-printed" },
    { "name": "tesseract", "status": "available",  "version": "5.x" }
  ]
}
```

---

### GET `/stats`
Verarbeitungsstatistiken seit Containerstart.

---

### POST `/ocr/process`
Einzelne Datei per OCR verarbeiten.

**Form-Data:**
| Feld       | Typ    | Default | Beschreibung |
|------------|--------|---------|--------------|
| `file`     | File   | –       | Bild (PNG/JPG/TIFF/BMP/WEBP) |
| `engine`   | string | `auto`  | `trocr` \| `tesseract` \| `auto` |
| `language` | string | `en`    | Sprachcode (Tesseract) |

**Response:**
```json
{
  "success": true,
  "text": "Extrahierter Text...",
  "engine_used": "trocr",
  "confidence": 0.97,
  "processing_time_ms": 420
}
```

---

### POST `/ocr/batch`
Mehrere Dateien in einem Request verarbeiten.

**Form-Data:** `files[]` (mehrere Uploads) + `engine`, `language`

**Response:**
```json
{
  "results": [
    { "filename": "page1.png", "text": "...", "engine_used": "trocr" },
    { "filename": "page2.png", "text": "...", "engine_used": "tesseract" }
  ],
  "total": 2,
  "success_count": 2
}
```

---

### POST `/ocr/process-folder`
Alle Dateien in einem Unterordner von `/data/input` verarbeiten.

**JSON Body:**
```json
{ "folder": "invoices", "engine": "auto", "language": "de" }
```

---

### POST `/pdf/analyze`
PDF analysieren: Text extrahieren + ggf. OCR je Seite.

**Form-Data:** `file` (PDF), `engine`, `language`

**Response:** Seitenweise Texte + Typ-Erkennung.

---

### POST `/pdf/analyze-type`
PDF-Typ klassifizieren.

**Response:**
```json
{ "type": "scanned", "confidence": 0.95, "pages_sampled": 3 }
```
Mögliche Typen: `digital` | `scanned` | `mixed`

---

### POST `/pdf/to-png`
Spezifische PDF-Seiten in PNG konvertieren.

**JSON Body:** `{ "file_path": "/data/input/doc.pdf", "pages": [1, 2, 3], "dpi": 150 }`

---

### POST `/pdf/to-png-all`
Alle Seiten eines PDFs in PNG konvertieren.

---

### GET `/pdf/page-count`
Seitenanzahl eines PDFs abfragen.

**Query-Params:** `?file_path=/data/input/doc.pdf`

---

### POST `/pdf/to-png-combined`
PDF-Seiten zu einem kombinierten Bild zusammenfügen.

---

### POST `/pdf/to-png-smart`
Intelligente PDF-to-PNG-Konvertierung mit automatischer Qualitätsanpassung und Größenbeschränkungen.

---

### POST `/debug/file-info`
Debug-Endpoint: Datei-Metadaten und Format-Details.

---

## Modelle

| Modell | Engine | Beschreibung |
|--------|--------|--------------|
| `microsoft/trocr-large-printed` | TrOCR | Optimiert für gedruckten Text, Rechnungen, Dokumente |
| Tesseract v5 | Tesseract | Klassisches OCR, gut für einfache Dokumente + DE/EN |

Das TrOCR-Modell wird beim ersten Start automatisch von Hugging Face heruntergeladen (~1.4 GB).
Für Air-Gapped-Umgebungen: Modell vorab in `ocr-service/models/` ablegen.

---

## Storage-Pfade

| Pfad (Host)             | Pfad (Container) | Verwendung |
|-------------------------|------------------|------------|
| `ocr_storage/input/`    | `/data/input`    | Eingabedateien |
| `ocr_storage/output/`   | `/data/output`   | OCR-Ergebnisse (JSON + Text) |
| `ocr_storage/temp/`     | `/data/temp`     | Temporäre Zwischendateien |

Alle Verzeichnisse werden beim ersten Start automatisch angelegt.
`.gitkeep`-Dateien sichern die Verzeichnisstruktur im Repository.

---

## N8N-Integration

Der Service wird über das `ocr-processing-workflow.json` angesteuert:

```
Webhook → Upload File → POST /ocr/process → Ergebnis verarbeiten → Supabase speichern
```

Für PDF-Workflows: `pdf-ocr-subflow.json` (Subworkflow) + `pdf-smart-processing-subflow.json`.

---

## Verwendung mit curl

```bash
# Einzelbild
curl -X POST http://ocr.brain.local/ocr/process \
  -F "file=@scan.png" \
  -F "engine=auto" \
  -F "language=de"

# Health check (kein Auth nötig wenn intern)
curl http://ocr-service:8002/health
```
