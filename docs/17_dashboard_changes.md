# 17. Dashboard – Architektur & Änderungen

Das Dashboard (`dashboard/`) ist eine vanilla-JS Single-Page-Application (kein Framework),
die hinter dem Caddy `forward_auth`-Middleware läuft.

---

## Dateien

| Datei | Rolle |
|-------|-------|
| `index.html` | HTML-Struktur, Service-Cards, Tab-Panels, CSS-Import |
| `style.css` | Layout, Dark-Mode, Cards, API-Cards, Modals |
| `auth.js` | Supabase-Session-Management, Login-Redirect, Token-Refresh |
| `main.js` | Entry-Point: lädt alle Module, setzt `DOMContentLoaded`-Handler |
| `health.js` | Polling der Service-Health-Endpunkte, Status-Anzeige |
| `control.js` | Admin-Aktionen: Backup, Restore, Service-Steuerung |
| `admin.js` | Admin-Tab-Logik: Tab-Switching, Status-Tabelle, Event-Log |
| `config.js` | Zentrale Konfiguration (Supabase-URL, API-Base-URLs) |
| `login.html` | Login-Seite (E-Mail + Passwort, TOTP-Prompt) |
| `macros.json` | Vordefinierte Control-Macros (JSON-Array) |

---

## Tab-Struktur

Das Dashboard hat drei Tabs:

```
┌──────────────────────────────────┐
│  [Services]  [Admin]  [Profile]  │
└──────────────────────────────────┘
```

| Tab | HTML-ID | Inhalt |
|-----|---------|--------|
| Services | `tab-services` | Service-Cards (n8n, Supabase, Open-WebUI…) + API-Cards |
| Admin | `tab-admin` | Status-Tabelle, Backup-Panel, Restore, Event-Log |
| Profile | `tab-profile` | Passwort ändern, Session-Info |

Tab-Aktivierung via URL-Hash (`#admin`, `#services`, `#profile`).
Nach Login springt `auth.js` über `window.activateDashboardTab` automatisch
in den zuletzt gespeicherten Tab.

---

## Card-Typen

### Service-Cards (`.card`)
Verlinken direkt auf die Web-UI des jeweiligen Service (neues Tab).
Link-URLs werden via `health.js` dynamisch aus der Config gesetzt.

```html
<a id="link-n8n" href="#" target="_blank" class="card">
  <h2>n8n</h2>
  <img src="assets/logos/n8n.svg" class="card-logo">
</a>
```

Service-Cards zeigen einen farbigen Status-Badge (grün/gelb/rot),
der durch `health.js` nach jedem Health-Check aktualisiert wird.

**Service-Cards:**
| ID | Service |
|----|---------|
| `link-n8n` | N8N Workflow Engine |
| `link-supabase` | Supabase Studio |
| `link-openwebui` | Open-WebUI (Chat) |
| `link-flowise` | Flowise AI Builder |
| `link-searxng` | SearXNG Search |

### API-Cards (`.api-card`)
Zeigen interne API-Services ohne eigene Web-UI.
Nicht anklickbar, dienen als Statusanzeige.

```html
<div id="link-ocr" class="api-card">
  <img src="assets/logos/python.svg" class="api-card-icon">
  <div class="api-card-info">
    <span class="api-card-name">OCR Service</span>
    <span class="api-card-desc">TrOCR · Tesseract · PDF</span>
    <code class="api-card-endpoint">ocr.brain.local/ocr/process</code>
  </div>
</div>
```

**API-Cards:**
| ID | Service |
|----|---------|
| `link-pythonNlp` | Python NLP Service (SpaCy, NER, GraphRAG) |
| `link-ocr` | OCR Service (TrOCR, Tesseract, PDF) |

---

## JS-Module-Bridges (`window.*`)

Die Module kommunizieren über `window`-Eigenschaften, da sie als separate `<script>`-Tags
geladen werden (kein ES-Module-System):

| Bridge | Definiert in | Aufgerufen von | Zweck |
|--------|-------------|----------------|-------|
| `window._health` | `health.js` | `control.js` | Health-Refresh nach Service-Neustart auslösen |
| `window._ctrl` | `control.js` | `admin.js` | Admin-Aktionen (backup, restart) ausführen |
| `window.activateDashboardTab` | `admin.js` | `auth.js` | Tab nach Login-Redirect aktivieren |

**Beispiel:**
```javascript
// control.js – nach Aktion Health neu laden
if (window._health) window._health.refresh();

// health.js – Bridge registrieren
window._health = { refresh: fetchStatus };

// control.js – Bridge registrieren
window._ctrl = { backup: triggerBackup, restart: restartService, ... };
```

---

## Auth-Flow

```
Browser → dashboard.brain.local
    │
    ▼
Caddy forward_auth → auth-gateway:5001/verify
    ├── 401 → redirect → login.html
    └── 200 → Dashboard laden
                │
                ▼
            auth.js prüft Supabase-Session (sb-access-token Cookie)
                ├── abgelaufen → Token-Refresh via Supabase SDK
                └── gültig     → Dashboard initialisieren
```

Das Login setzt einen `sb-access-token`-Cookie (HttpOnly, SameSite=Lax).
Caddy liest diesen Cookie als Fallback, falls kein `Authorization`-Header vorhanden ist.

---

## Whisper STT (Speech-to-Text)

Whisper läuft **innerhalb des `open-webui`-Containers** als integriertes faster-whisper-Modell.
Es ist kein separater Service.

**Konfiguration in `docker-compose.yml`:**
```yaml
open-webui:
  environment:
    # Whisper STT – faster-whisper läuft direkt im Container
    # Modelle: tiny | base | small | medium | large-v3
    # Ändern: WHISPER_MODEL in .env → docker compose up -d open-webui
    - WHISPER_MODEL=${WHISPER_MODEL:-medium}
```

**`.env`-Variable:**
```bash
WHISPER_MODEL=medium    # tiny | base | small | medium | large-v3
```

Das Modell wird beim ersten Start von Hugging Face heruntergeladen
und im Open-WebUI-Volume gecacht (`open-webui` Docker Volume).

**Dashboard-Integration:** Der Open-WebUI-Card-Status spiegelt indirekt die Whisper-Verfügbarkeit wider.
Ein dedizierter Whisper-Status ist nicht implementiert (kein separater Health-Endpunkt).

---

## Supabase CDN (SRI-Sicherung)

Das Supabase JS SDK wird von CDN geladen mit gepinnter Version und SRI-Hash:

```html
<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.97.0/dist/umd/supabase.js"
  integrity="sha384-..."
  crossorigin="anonymous">
</script>
```

Dies verhindert Supply-Chain-Angriffe über CDN-Kompromittierung.

---

## Lokale Entwicklung

```bash
# Dashboard direkt aus dem Dateisystem öffnen (kein Build-Schritt nötig)
open dashboard/index.html

# Oder über den Stack (mit Auth):
# https://dashboard.brain.local
```

Alle Änderungen sind sofort wirksam (kein Compile-Schritt).
