# 2. Konfiguration (`.env`)

Kopiere `.env.example` nach `.env` und trage alle Pflichtfelder ein.

---

## Secrets generieren

```bash
openssl rand -hex 32   # für die meisten Keys (64 Zeichen)
openssl rand -hex 16   # für 32-Zeichen-Keys (z.B. POSTGRES_PASSWORD)
```

Supabase `ANON_KEY` und `SERVICE_ROLE_KEY` über den offiziellen Generator:
→ https://supabase.com/docs/guides/self-hosting/docker#generate-api-keys

---

## Pflichtfelder

### n8n
| Variable | Beschreibung |
|---|---|
| `N8N_ENCRYPTION_KEY` | Verschlüsselt gespeicherte Credentials (`openssl rand -hex 32`) |
| `N8N_USER_MANAGEMENT_JWT_SECRET` | JWT-Secret für n8n User Management |
| `N8N_RUNNERS_AUTH_TOKEN` | Gemeinsames Secret von n8n und dem Task-Runner-Sidecar `n8n-runners` (`openssl rand -hex 32`). Fehlt es, bricht `docker compose` mit einer Meldung ab |

> **Achtung:** Ohne `N8N_ENCRYPTION_KEY` sind gespeicherte n8n-Credentials nach einem Restore unbrauchbar. Die `.env` getrennt und sicher sichern (siehe [08_backup_and_recovery.md](08_backup_and_recovery.md)).

### Supabase
| Variable | Beschreibung |
|---|---|
| `POSTGRES_PASSWORD` | DB-Passwort (kein `%` verwenden, `openssl rand -hex 16`) |
| `JWT_SECRET` | Basis für Supabase JWTs (`openssl rand -hex 32`) |
| `ANON_KEY` | Öffentlicher API-Key (aus JWT-Generator) |
| `SERVICE_ROLE_KEY` | Admin-Key (aus JWT-Generator, geheim halten!) |
| `DASHBOARD_USERNAME` | Supabase Studio Login |
| `DASHBOARD_PASSWORD` | Supabase Studio Passwort |
| `POOLER_TENANT_ID` | Beliebige Zahl (z.B. `12345`) |
| `SECRET_KEY_BASE` | `openssl rand -hex 64` |
| `VAULT_ENC_KEY` | Genau 32 Zeichen: `openssl rand -hex 16` |
| `LOGFLARE_PUBLIC_ACCESS_TOKEN` | `openssl rand -hex 32` |
| `LOGFLARE_PRIVATE_ACCESS_TOKEN` | `openssl rand -hex 32` (verschieden vom PUBLIC) |
| `STUDIO_DEFAULT_ORGANIZATION` | Anzeigename in Supabase Studio |
| `PG_META_CRYPTO_KEY` | Verschlüsselung in postgres-meta/Studio (`openssl rand -hex 32`) |

### Neo4j
| Variable | Beschreibung |
|---|---|
| `NEO4J_AUTH` | Format: `neo4j/passwort` (z.B. `neo4j/$(openssl rand -hex 16)`) |

### S3 Storage (für Supabase Storage)
| Variable | Beschreibung |
|---|---|
| `S3_PROTOCOL_ACCESS_KEY_ID` | `openssl rand -hex 16` (32 Zeichen) |
| `S3_PROTOCOL_ACCESS_KEY_SECRET` | `openssl rand -hex 32` (64 Zeichen) |

### Zugriffskontrolle (auth-gateway)
| Variable | Beschreibung |
|---|---|
| `SUPERADMIN_EMAILS` | Kommagetrennt. Voller Zugriff inkl. Restore und User-Management. Für Team-Betrieb setzen |
| `ADMIN_EMAILS` | Service start/stop, Macros, Backup erstellen. Fail-closed: leer = nur Superadmins |
| `MFA_REQUIRED` | `true` (Standard): auth-gateway verlangt `aal2` (Passwort + TOTP). `false` nur als Notfall-Schalter |

### Grafana
| Variable | Beschreibung |
|---|---|
| `GRAFANA_ADMIN_PASSWORD` | Admin-Passwort (`openssl rand -hex 16`) |
| `GRAFANA_ADMIN_EMAIL` | Benutzer mit dieser E-Mail erhält die Grafana-Admin-Rolle |
| `GRAFANA_PROXY_WHITELIST` | Optional: Trust-Header nur aus diesem Subnetz (z. B. `172.18.0.0/16`) |
| `GRAFANA_PG_PASSWORD` | Optional: Rolle `grafana_intune_reader`, siehe [28_intune_inventory.md](28_intune_inventory.md) |
| `GRAFANA_TEAMS_WEBHOOK_URL` | Optional: Teams-Webhook für Grafana-Alerting |
| `GF_INSTALL_PLUGINS`, `GRAFANA_OPCUA_ENDPOINT` | Optional: OPC-UA-Plugin und Endpunkt, siehe [24_sps_monitoring.md](24_sps_monitoring.md) |

### Hermes Agent / Teams
Siehe [21_hermes_agent.md](21_hermes_agent.md) und [25_teams_bot.md](25_teams_bot.md).

| Variable | Beschreibung |
|---|---|
| `HERMES_DASHBOARD_USER`, `HERMES_DASHBOARD_PASSWORD`, `HERMES_DASHBOARD_AUTH_SECRET` | Basic-Auth des Hermes-Dashboards (Vorbedingung von Hermes; eigentliche Zugriffskontrolle ist Caddy `forward_auth`) |
| `HERMES_UID`, `HERMES_GID` | Besitzer der Dateien im Volume `hermes_data` |
| `AUTOSTART_HERMES` | `true`: Hermes startet mit dem Stack |
| `TEAMS_CLIENT_ID`, `TEAMS_CLIENT_SECRET`, `TEAMS_TENANT_ID` | Azure-AD-App des Teams-Gateways |
| `TEAMS_ALLOWED_USERS` | Kommagetrennte AAD-Object-IDs oder UPNs |
| `TEAMS_PORT` | Webhook-Port (Standard `3978`) |

### Weitere Dienste
| Variable | Beschreibung |
|---|---|
| `SPS_MQTT_BROKER` | MQTT-Broker für `mqtt2prometheus` (Profil `monitoring`) |
| `WHISPER_MODEL` | Speech-to-Text-Modell in Open WebUI (`tiny` … `large-v3`, Standard `medium`) |
| `REDIS_HOST`, `REDIS_PORT`, `REDIS_AUTH` | Valkey/Redis für SearXNG |
| `SEARXNG_UWSGI_WORKERS`, `SEARXNG_UWSGI_THREADS` | SearXNG-Performance |
| `BACKUP_INTERVAL_H` | Backup-Intervall in Stunden (Profil `backup`) |
| `IS_PUBLIC_PROFILE` | Supabase-Studio-Profil |

### Supabase-Defaults
Der Block `DEFAULTS` in `.env.example` (GoTrue, Mailer, Studio, Supavisor, Kong, PostgREST, Functions, `DOCKER_SOCKET_LOCATION`, Google Cloud) entspricht den Standardwerten des Supabase-Self-Hostings und muss lokal nicht angepasst werden. Bedeutung der Variablen: [Supabase Self-Hosting mit Docker](https://supabase.com/docs/guides/self-hosting/docker). Für Produktion mindestens `SITE_URL`, `API_EXTERNAL_URL`, `SUPABASE_PUBLIC_URL` und die SMTP-Werte anpassen.

---

## Domain & Hostnamen

### Lokal (Standard)

```bash
DOMAIN=brain.local

DASHBOARD_HOSTNAME=brain.local
N8N_HOSTNAME=n8n.brain.local
WEBUI_HOSTNAME=webui.brain.local
SUPABASE_HOSTNAME=supabase.brain.local
NEO4J_HOSTNAME=neo4j.brain.local
CRAWL4AI_HOSTNAME=crawl.brain.local
SEARXNG_HOSTNAME=search.brain.local
QDRANT_HOSTNAME=qdrant.brain.local
GRAFANA_HOSTNAME=grafana.brain.local
HERMES_HOSTNAME=agent.brain.local

LETSENCRYPT_EMAIL=internal
```

Die `/etc/hosts`-Einträge dazu: siehe [01_installation.md](01_installation.md).

### Produktion (Server)

```bash
DOMAIN=yourdomain.com

DASHBOARD_HOSTNAME=brain.yourdomain.com
N8N_HOSTNAME=n8n.yourdomain.com
WEBUI_HOSTNAME=webui.yourdomain.com
SUPABASE_HOSTNAME=supabase.yourdomain.com
NEO4J_HOSTNAME=neo4j.yourdomain.com
CRAWL4AI_HOSTNAME=crawl.yourdomain.com
SEARXNG_HOSTNAME=search.yourdomain.com
QDRANT_HOSTNAME=qdrant.yourdomain.com
GRAFANA_HOSTNAME=grafana.yourdomain.com
HERMES_HOSTNAME=agent.yourdomain.com

LETSENCRYPT_EMAIL=info@yourdomain.com
```

Caddy holt dann automatisch Let's Encrypt-Zertifikate.

---

## Optionale Felder

```bash
# Ollama-Endpunkt (Mac: host.docker.internal, Server mit Ollama-Container: http://ollama:11434)
OLLAMA_HOST=http://host.docker.internal:11434

# OCR-Modell (muss vorab gepullt werden: ollama pull glm-ocr)
OCR_MODEL=glm-ocr

# Signup nach erstem User-Setup deaktivieren
DISABLE_SIGNUP=true

# OpenAI (für Supabase SQL-Editor-Assistent)
# OPENAI_API_KEY=

# Google OAuth für Supabase
# ENABLE_GOOGLE_SIGNUP=true
# GOOGLE_CLIENT_ID=
# GOOGLE_CLIENT_SECRET=
```

---

## Wichtige Hinweise

- **Keine `%`-Zeichen** im `POSTGRES_PASSWORD`
- `ANON_KEY` und `SERVICE_ROLE_KEY` müssen zum selben `JWT_SECRET` passen
- Kommentare hinter einem Wert (` # …`) in `JWT_SECRET`, `ANON_KEY` und `SERVICE_ROLE_KEY` gehören nicht zum Wert; Docker Compose entfernt sie. Eigene Skripte (z. B. `cut -d= -f2-`) müssen sie ebenfalls abtrennen, sonst ergeben Signaturprüfung und Header-Tests falsche 401-Fehler
- Nach dem ersten User-Setup `DISABLE_SIGNUP=true` setzen und Stack neu starten
- Secrets nie in Git committen – `.env` ist in `.gitignore`
