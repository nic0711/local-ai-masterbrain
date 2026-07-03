# 15. API Reference

Vollständige Endpunkt-Übersicht für alle selbst entwickelten Services im Stack.
Für Drittanbieter-Services (Supabase REST/Auth, n8n, Ollama) siehe die jeweiligen upstream-Docs.

---

## Übersicht

| Service | Base URL (intern) | Base URL (extern) | Endpunkte |
|---------|-------------------|-------------------|-----------|
| auth-gateway | `http://auth-gateway:5001` | `https://auth.{DOMAIN}` | 18 |
| python-nlp-service | `http://python-nlp-service:8001` | `https://nlp.{DOMAIN}` | 10 |
| ocr-service | `http://ocr-service:8002` | `https://ocr.{DOMAIN}` | 15 |
| tts-service | `http://tts-service:8003` | `https://tts.{DOMAIN}` | 7 |

---

## auth-gateway (Port 5001)

Auth-Level: **Auth** = gültiges JWT erforderlich · **Admin** = zusätzlich in `ADMIN_EMAILS` eingetragen (siehe [05_security_hardening.md](05_security_hardening.md))

| Methode | Pfad | Auth | Beschreibung |
|---------|------|------|--------------|
| `GET` | `/health` | – | Health-Check (öffentlich) |
| `GET` | `/status` | Auth | Service-Status (alle auth. Nutzer) |
| `GET` | `/verify` | – | JWT verifizieren (Caddy `forward_auth` target) |
| `GET` | `/control/backup/status` | Auth | Status des letzten Backups |
| `GET` | `/control/backup/list` | Auth | Verfügbare Backup-Archive auflisten |
| `GET` | `/control/services/status` | Auth | Status aller Docker-Services |
| `GET` | `/control/macros` | Auth | Verfügbare Control-Macros auflisten |
| `POST` | `/control/backup` | **Admin** | Backup erstellen |
| `GET` | `/control/backup/files` | **Admin** | Dateien innerhalb eines Backups |
| `GET` | `/control/backup/diff` | **Admin** | Diff zwischen zwei Backups |
| `POST` | `/control/restore` | **Admin** | Backup wiederherstellen |
| `GET` | `/control/users` | **Admin** | Supabase-Benutzer auflisten |
| `POST` | `/control/users` | **Admin** | Neuen Benutzer anlegen |
| `POST` | `/control/users/password` | **Admin** | Passwort zurücksetzen |
| `POST` | `/control/users/delete` | **Admin** | Benutzer löschen |
| `POST` | `/control/services/{service}/{action}` | **Admin** | Service starten / stoppen / neustarten |
| `GET` | `/control/services/{service}/logs` | **Admin** | Service-Logs abrufen |
| `POST` | `/control/macro/{macro_id}` | **Admin** | Control-Macro ausführen |

### POST `/control/backup`
```json
// Request body (optional)
{ "include_env": false }

// Response
{ "success": true, "backup_file": "backup-2026-03-15T12:00:00.tar.gz", "size_mb": 42 }
```

### GET `/verify`
Wird von Caddy als `forward_auth` aufgerufen. Gibt `200 OK` zurück wenn das JWT gültig ist, sonst `401`.

### GET `/control/services/status`
Gibt den laufenden Status aller kontrollierbaren Docker-Services zurück.

```json
{
  "n8n": "up", "open-webui": "up", "flowise": "down",
  "neo4j": "down", "minio": "up", "clickhouse": "up",
  "langfuse-web": "up", "langfuse-worker": "down"
}
```

### POST `/control/services/{service}/{action}`
`action` = `start` | `stop` | `restart`

**Optionale Services** (starten nicht automatisch beim Stack-Start, werden bei `start` per `docker compose --profile optional up -d` erstellt falls kein Container existiert):
`neo4j` · `flowise` · `minio` · `clickhouse` · `langfuse-web` · `langfuse-worker`

```bash
curl -X POST https://auth.brain.local/control/services/neo4j/start \
  -H "Authorization: Bearer $TOKEN"

# Response
{ "status": "ok", "message": "neo4j gestartet (compose)" }
```

### POST `/control/macro/{macro_id}`
Führt ein vordefiniertes Macro aus (`dashboard/macros.json`).

| Macro-ID | Beschreibung |
|---|---|
| `light-mode` | Nur n8n + Open WebUI |
| `research` | SearXNG + Crawl4AI + Open WebUI + n8n |
| `rag-mode` | Qdrant + Neo4j + NLP + Open WebUI + n8n |
| `langfuse-start` | MinIO + ClickHouse + Langfuse starten |
| `save-resources` | Alle optionalen Services stoppen |
| `restart-core` | n8n + Open WebUI + Flowise neustarten |

```bash
curl -X POST https://auth.brain.local/control/macro/langfuse-start \
  -H "Authorization: Bearer $TOKEN"

# Response
{ "status": "ok", "macro": "langfuse-start", "results": ["start minio: ok", ...], "errors": [] }
```

---

## python-nlp-service (Port 8001)

| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| `GET` | `/health` | Health-Check |
| `GET` | `/status` | Version und NLP-Modell-Info |
| `POST` | `/process` | Dokument analysieren (PDF/Text, NLP-Pipeline) |
| `POST` | `/pdf/analyze-type` | PDF-Typ erkennen (digital/scanned/mixed) |
| `POST` | `/pdf/to-png-smart` | PDF → PNG (intelligente Qualitätswahl) |
| `POST` | `/pdf/extract` | Text aus PDF extrahieren (nativ + OCR-Fallback) |
| `POST` | `/document/analyze` | Vollständige Dokumentenanalyse (Layout + NLP) |
| `POST` | `/graph/init` | Neo4j-Schema initialisieren |
| `POST` | `/graph/index` | Obsidian-Notiz in Knowledge Graph indexieren |
| `POST` | `/graph/query` | Knowledge Graph nach Entitäten/Titeln abfragen |

### POST `/process`
```json
// Request (multipart/form-data)
// file: PDF oder Textdatei

// Response
{
  "title": "Dokument-Titel",
  "text": "Extrahierter Text...",
  "entities": [{ "text": "Berlin", "label": "GPE" }],
  "summary": "Kurzzusammenfassung...",
  "language": "de",
  "processing_time_ms": 850
}
```

### POST `/graph/index`
```json
// Request
{
  "title": "Notiz-Titel",
  "content": "# Notiz\n\n[[Link]] #tag",
  "path": "Notes/Notiz-Titel.md",
  "metadata": { "created": "2026-03-15" }
}

// Response
{ "success": true, "node_id": "notiz_titel_1710503600000", "relationships_created": 3 }
```

### POST `/graph/query`
```json
// Request
{ "query": "Berlin Klimawandel", "limit": 10 }

// Response
{
  "results": [
    { "title": "Klimapolitik", "score": 0.87, "path": "Notes/Klimapolitik.md" }
  ]
}
```

---

## ocr-service (Port 8002)

Vollständige Beschreibung aller Endpunkte: [14_ocr_service.md](14_ocr_service.md)

| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| `GET` | `/` | Root health check |
| `GET` | `/health` | Engine-Status, Verzeichnisse |
| `GET` | `/engines` | Verfügbare OCR-Engines |
| `GET` | `/stats` | Verarbeitungsstatistiken |
| `POST` | `/ocr/process` | Einzelbild per OCR verarbeiten |
| `POST` | `/ocr/batch` | Mehrere Dateien batch-verarbeiten |
| `POST` | `/ocr/process-folder` | Ordner verarbeiten |
| `POST` | `/pdf/analyze` | PDF analysieren + OCR |
| `POST` | `/pdf/analyze-type` | PDF-Typ klassifizieren |
| `POST` | `/pdf/to-png` | PDF-Seiten → PNG |
| `POST` | `/pdf/to-png-all` | Alle Seiten → PNG |
| `GET` | `/pdf/page-count` | Seitenanzahl |
| `POST` | `/pdf/to-png-combined` | Seiten zusammenführen |
| `POST` | `/pdf/to-png-smart` | Smart-Konvertierung |
| `POST` | `/debug/file-info` | Datei-Metadaten |

---

---

## tts-service (Port 8003)

Vollständige Beschreibung: [18_tts_service.md](18_tts_service.md)

| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| `GET` | `/health` | Engine-Status, Gerät, Voices, Disk |
| `GET` | `/voices` | Gespeicherte Referenzstimmen auflisten |
| `POST` | `/tts/synthesize` | Text → WAV (mit optionaler Referenzstimme) |
| `POST` | `/tts/clone` | Text + Referenz-Audio (multipart) → WAV |
| `POST` | `/dub/video` | Video-Upload oder YouTube-URL → `job_id` |
| `GET` | `/dub/status/{job_id}` | Dubbing-Fortschritt (0.0–1.0) |
| `GET` | `/dub/download/{job_id}` | Fertiges Video herunterladen |

### POST `/tts/synthesize`
```json
// Request
{ "text": "Hallo Welt", "language": "de", "voice_id": "meine_stimme" }

// Response: audio/wav
```

### POST `/tts/clone`
```bash
curl -X POST https://tts.brain.local/tts/clone \
  -F "text=Geklonte Stimme" \
  -F "reference_audio=@stimme.wav" \
  -F "save_as=meine_stimme" \
  --output clone.wav
```

### POST `/dub/video`
```json
// YouTube-URL
{ "youtube_url": "https://youtu.be/...", "target_language": "de", "voice_id": "meine_stimme" }

// Response
{ "job_id": "3f8a2b1c-..." }
```

### GET `/dub/status/{job_id}`
```json
{ "job_id": "...", "status": "synthesizing", "progress": 0.65, "download_url": null }
```

---

## N8N API Reference Workflow

Der Workflow `api-health-reference.json` stellt alle Endpunkte dynamisch bereit:

```bash
# Alle Services
curl "http://n8n.brain.local/webhook/api-reference?service=all"

# Einzelner Service
curl "http://n8n.brain.local/webhook/api-reference?service=ocr"
```

**Response-Schema:**
```json
{
  "generated_at": "2026-03-15T12:00:00.000Z",
  "total_services": 4,
  "services": [
    {
      "service": "ocr-service",
      "base_url": "http://ocr-service:8002",
      "status": "healthy",
      "health_raw": { ... },
      "endpoints": [
        { "method": "GET", "path": "/health", "description": "..." }
      ]
    }
  ]
}
```

---

## Authentifizierung

Alle externen Endpunkte (über `{DOMAIN}`) sind hinter Caddy `forward_auth` geschützt.
Interner Zugriff (Container-zu-Container) ist ohne Auth möglich.

```bash
# Extern – mit Session-Cookie (nach Login)
curl -b "sb-access-token=$TOKEN" https://ocr.brain.local/health

# Intern – direkt
curl http://ocr-service:8002/health
```
