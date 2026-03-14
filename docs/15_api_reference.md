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

---

## auth-gateway (Port 5001)

Alle `/control/*`-Routen erfordern ein gültiges JWT (Cookie `sb-access-token` oder `Authorization: Bearer`).

| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| `GET` | `/health` | Detaillierter Health-Check (DB, Supabase) |
| `GET` | `/status` | Version und Uptime |
| `GET` | `/verify` | JWT verifizieren (Caddy `forward_auth` target) |
| `POST` | `/control/backup` | Datenbank-Backup auslösen |
| `GET` | `/control/backup/status` | Status des letzten Backups |
| `GET` | `/control/backup/list` | Verfügbare Backup-Archive auflisten |
| `GET` | `/control/backup/files` | Dateien innerhalb eines Backups |
| `GET` | `/control/backup/diff` | Diff zwischen zwei Backups |
| `GET` | `/control/users` | Supabase-Benutzer auflisten |
| `POST` | `/control/users` | Neuen Benutzer anlegen |
| `POST` | `/control/users/password` | Passwort ändern |
| `POST` | `/control/users/delete` | Benutzer löschen |
| `GET` | `/control/services/status` | Status aller Docker-Services |
| `POST` | `/control/services/{service}/{action}` | Service starten / stoppen / neustarten |
| `GET` | `/control/services/{service}/logs` | Service-Logs abrufen |
| `GET` | `/control/macros` | Verfügbare Control-Macros auflisten |
| `POST` | `/control/macro/{macro_id}` | Control-Macro ausführen |
| `POST` | `/control/restore` | Datenbank aus Backup wiederherstellen |

### POST `/control/backup`
```json
// Request body (optional)
{ "include_env": false }

// Response
{ "success": true, "backup_file": "backup-2026-03-15T12:00:00.tar.gz", "size_mb": 42 }
```

### GET `/verify`
Wird von Caddy als `forward_auth` aufgerufen. Gibt `200 OK` zurück wenn das JWT gültig ist, sonst `401`.

### POST `/control/services/{service}/{action}`
`action` = `start` | `stop` | `restart`

```bash
curl -X POST https://auth.brain.local/control/services/ocr-service/restart \
  -H "Authorization: Bearer $TOKEN"
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
