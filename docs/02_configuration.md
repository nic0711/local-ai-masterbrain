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

### Neo4j
| Variable | Beschreibung |
|---|---|
| `NEO4J_AUTH` | Format: `neo4j/passwort` (z.B. `neo4j/$(openssl rand -hex 16)`) |

### S3 Storage (für Supabase Storage)
| Variable | Beschreibung |
|---|---|
| `S3_PROTOCOL_ACCESS_KEY_ID` | `openssl rand -hex 16` (32 Zeichen) |
| `S3_PROTOCOL_ACCESS_KEY_SECRET` | `openssl rand -hex 32` (64 Zeichen) |

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
- Nach dem ersten User-Setup `DISABLE_SIGNUP=true` setzen und Stack neu starten
- Secrets nie in Git committen – `.env` ist in `.gitignore`
