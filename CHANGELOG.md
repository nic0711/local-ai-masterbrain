# Changelog

Chronologische Änderungshistorie (neueste zuerst). Die README verweist nur hierher.

### 2026-11 – Image-Pinning, auth-gateway ohne Docker-CLI, externe n8n-Task-Runner

| Was | Details |
|-----|---------|
| **Alle Images exakt gepinnt** | Kein `:latest` mehr im Stack (n8n 2.49.5, Ollama, Open WebUI, Qdrant, Grafana, Neo4j, Crawl4AI, SearXNG, Prometheus-Stack, cAdvisor u. a.); Dependabot (`docker-compose`) schlägt Updates wöchentlich vor, n8n bleibt unter v3.0 (#223) |
| **modbus-exporter entfernt** | Service, `sps-monitoring/modbus.yml`, Prometheus-Job und Dashboard-Einträge entfernt; SPS-Monitoring läuft über MQTT und OPC-UA (#223) |
| **auth-gateway ohne Docker-CLI/Compose** | Service-Control nur noch über das Docker-SDK; die Go-Binaries brachten wiederholt nicht behebbare Upstream-CVEs mit. Optionale Services ohne vorhandenen Container liefern `409` mit dem einmaligen Host-Befehl (#223, s. [docs/19_on_demand_services.md](docs/19_on_demand_services.md)) |
| **Security-Lockfiles** | multidict 6.9.1 und setuptools 84.1.0 in ocr-/tts-service (#226) |
| **Externe n8n-Task-Runner** | Code-Nodes laufen im Sidecar `n8n-runners` (`n8nio/runners`, gleiche Version wie n8n) statt als Kindprozess von n8n; neues Secret `N8N_RUNNERS_AUTH_TOKEN`; Builtin-Allowlist in `n8n/task-runners.json`; Dependabot-Gruppe `n8n` (#227) |

### 2026-10 – CVE-Monitoring, Security-Rebuild, Supabase-Fixes

| Was | Details |
|-----|---------|
| **CVE-Monitoring** | Wöchentlicher `cve-watch`-Workflow mit Trivy gegen die laufenden Images (#211–#215), OmniVoice-Versionscheck gegen PyPI (#204) |
| **Image-Updates** | Supabase-Services, Postgres 15.19, n8n, nginx, Uptime Kuma, Hermes (#211), storage-api v1.84.23 (#217) |
| **Dependency-Fixes** | urllib3 2.8.0 in allen vier eigenen Images (#203), msgpack 1.2.3 im tts-service (#218) |
| **Hermes-Overlay** | Gepinnte Python-Abhängigkeiten (aiohttp, yarl, urllib3, tornado, certifi, anyio, httpx2 u. a.) plus `apt-get upgrade` (#219, #221) |
| **Blackbox-Monitoring** | `prom/blackbox-exporter` für Erreichbarkeitsprüfungen (#202, s. [docs/23_monitoring.md](docs/23_monitoring.md)) |
| **Storage-Upload repariert** | Supabase-Storage nutzt das benannte Volume `supabase_storage_data` statt eines macOS-Bind-Mounts (xattr-Fehler `ENOTSUP`) (#220) |
| **Nutzeranlage repariert** | `create_user_profile()` als `SECURITY DEFINER` mit festem `search_path` (#222) |
| **Deployment-Doku** | Backup-, Deployment- und Rollback-Verfahren dokumentiert (#210, s. [docs/handbook/04-updates-und-rollback.md](docs/handbook/04-updates-und-rollback.md)) |

### 2026-09 – Stabilisierung, Stack verschlankt

| Was | Details |
|-----|---------|
| **Langfuse, MinIO, ClickHouse, Flowise entfernt** | Services, Caddy-Routen, Dashboard-Kacheln und Doku-Einträge entfernt (#198) |
| **n8n gepinnt** | 2.37.6 statt `:latest`, Updates per Dependabot unter v3.0 (#185) |
| **Dependabot pausiert** | Automatische Versions-PRs während der Stabilisierung abgeschaltet (#196); Security-Updates laufen weiter |
| **OCR-Engines lazy** | OCR-Modelle werden erst bei Bedarf geladen, nicht beim Modul-Import (#183) |
| **Offene Punkte** | [docs/planning/OPEN_ITEMS.md](docs/planning/OPEN_ITEMS.md) aus dem Stabilisierungslauf (#193) |

### 2026-08 – Phase-1-Governance-Baseline (CI, Supply Chain, Architektur)

| Was | Details |
|-----|---------|
| **Architektur-Baseline integriert** | `CONTEXT.md` und 10 ADRs (`docs/adr/0001`–`0010`) sowie der Umsetzungsplan (`docs/planning/implementation-roadmap.md`) wurden aus der zuvor lokal vorbereiteten Zielarchitektur ins Repository übernommen |
| **CI/Supply-Chain-Governance** | Erstmaliger `.github/workflows/ci.yml`: YAML-/Workflow-Lint, Compose-Config-Prüfung, Custom-Image-Builds, Trivy-Repo-/Image-Scan mit strukturiertem Ausnahmeprozess (`docs/planning/security-exceptions/`), Secret-Scan, CycloneDX-SBOM, SARIF-Upload |
| **CODEOWNERS & Dependabot** | `.github/CODEOWNERS` (vorbereitet, Einzelowner-Blocker dokumentiert), `.github/dependabot.yml` |
| **Bekannte Bestandsfindings sichtbar gemacht** | `docs/planning/image-pinning-baseline.yml` (Third-Party-`latest`-Images), `docs/planning/test-coverage-gaps.md` (`tts-service` ohne Tests) — Behebung ist Phase 2/3, hier nur dokumentiert |
| **Manuelle GitHub-Einstellungen dokumentiert** | `docs/planning/github-manual-settings.md` — Branch-Protection, Secret-Scanning-Toggle etc. erfordern Repo-Admin-Aktion, wurden durch diesen PR nicht selbst gesetzt |

### 2026-07 – HttpOnly-Session-Cookie, CodeQL-Härtung

| Was | Details |
|-----|---------|
| **HttpOnly-Session-Cookie** | `sb-access-token` wurde bisher per `document.cookie` im Browser gesetzt – für jedes im Dashboard laufende JavaScript lesbar, eine XSS-Lücke hätte den Token direkt stehlen können. Der auth-gateway setzt den Cookie jetzt selbst per `Set-Cookie` (`HttpOnly` + `Secure`); `supabase-js` behält seine Session unverändert in `localStorage` |
| **Neue Endpoints** | `POST /session` (Token verifizieren + Cookie setzen, aal2-Pflicht) und `POST /session/logout` (Cookie löschen), Caddy-Routen `/_auth/session(/logout)` |
| **CodeQL-Alerts behoben** | 8 offene Code-Scanning-Alerts (Stack-Trace-Exposure in ocr-service/python-nlp-service, polynomialer ReDoS in der Wikilink-Regex, Path-Injection-Härtung in tts-service) – keine dismissed, alle per Code-Fix geschlossen |
| `auth-gateway/app.py` | `_get_verified_user`/`_verify_token_string`-Refactor, `/session`, `/session/logout`, `_COOKIE_DOMAIN` |
| `dashboard/auth.js` | `setCookie`/`clearCookie` async über Server-Roundtrip, `_readJWTPayload` entfernt (Cookie nicht mehr lesbar) |
| `ocr-service`, `python-nlp-service`, `tts-service` | Exception-Details bleiben im Server-Log statt in der Response; Wikilink-Regex mit begrenzter Gruppenlänge; Pfad-Sanitisierung CodeQL-erkennbar gemacht |
| `docs/05_security_hardening.md`, `docs/15_api_reference.md` | HttpOnly-Cookie-Architektur, `/session`-Endpoints dokumentiert |

### 2026-07 – Security-Fix: MFA-Bypass geschlossen, RBAC fail-closed

| Was | Details |
|-----|---------|
| **MFA-Bypass geschlossen** | `auth-gateway` prüfte den `aal`-Claim (Multi-Factor-Level) bisher nie – ein reines Passwort-Token (`aal1`) wurde von `/verify` akzeptiert, obwohl TOTP im Login-Formular sichtbar abgefragt wurde. 2FA schützte damit nur die Login-UI, nicht die dahinterliegenden Dienste. `/verify` verlangt jetzt `aal2`, Default `MFA_REQUIRED=true` |
| **RBAC fail-closed** | Ohne `ADMIN_EMAILS`/`SUPERADMIN_EMAILS` hatte bisher jeder authentifizierte Nutzer Admin-Rechte; `_require_admin`/`_require_superadmin` geben jetzt bei fehlender Konfiguration `False` zurück |
| **Grafana Header-Spoofing geschlossen** | `X-Forwarded-User`/`X-Forwarded-Role` wurden auf den auth-freien Pfaden `/public/*`, `/avatar/*` und dem Static-Asset-Bypass ungefiltert durchgereicht – Caddy strippt sie dort jetzt explizit; Static-Bypass für Grafana entfernt |
| **JWT-Cache-Fenster geschlossen** | Cache-Ablauf war fix 5 Minuten unabhängig vom Token-`exp` – jetzt am `exp` gedeckelt |
| **Cookie `Secure`-Flag** | Wurde auf `.local`-Domains bewusst weggelassen – jetzt immer bei `https:` gesetzt |
| **2FA-Recovery** | Neuer Superadmin-Endpoint `POST /control/users/mfa-reset` + Button „2FA zurücksetzen" in der Benutzerverwaltung, verhindert Lockout bei verlorenem Authenticator |
| `auth-gateway/app.py` | `aal`-Extraktion, `_require_aal2()`, Cache-Cap, fail-closed RBAC, `/control/users/mfa-reset` |
| `auth-gateway/tests/test_app.py` | 16 neue Tests (aal1/aal2, Cache-Cap, fail-closed, MFA-Reset) – 54/54 grün |
| `dashboard/auth.js` | Step-up-Flow auf `login.html`, Enrollment-Gate in `protectPage()`, Cookie immer `Secure` bei HTTPS |
| `dashboard/admin.js` | „2FA zurücksetzen"-Button in der Benutzerverwaltung |
| `Caddyfile` | Header-Stripping Grafana, Static-Asset-Ausnahme verengt (`.map`/`.txt`/`.xml` entfernt), Route für MFA-Reset |
| `docker-compose.yml` | `GRAFANA_PROXY_WHITELIST` (defense-in-depth für Grafana Auth-Proxy) |
| `.env.example` | `MFA_REQUIRED`, `GRAFANA_PROXY_WHITELIST` dokumentiert |
| `docs/05_security_hardening.md` | MFA-Erzwingung, fail-closed RBAC, Grafana-Header-Fix, Cookie-Flag, MFA-Reset-Endpoint dokumentiert |
| `docs/15_api_reference.md` | `/control/users/mfa-reset` ergänzt, Auth-Level um `aal2`-Anforderung erweitert |

### 2026-07 – Fokus auf Hermes Agent: Odysseus entfernt, Dashboard aufgeräumt

| Was | Details |
|-----|---------|
| **Odysseus entfernt** | AI-Workspace vollständig entfernt (Git-Submodul, Compose-Services, Caddy-Route, Dashboard-Karte, `docs/22_odysseus_workspace.md`) – Fokus liegt jetzt klar auf Hermes Agent |
| **Hermes aufgewertet** | Eigenes Logo statt generischem Python-Icon, prominentere Dashboard-Position, `HERMES_HOSTNAME`-Env-Bug im `dashboard`-Service behoben |
| **Hermes-Dashboard-Bugfix** | Container band nicht an `0.0.0.0` mangels Auth-Provider → `HERMES_DASHBOARD_USER/PASSWORD/AUTH_SECRET` als Pflichtfelder ergänzt (siehe Hinweis oben) |
| **Zentraler Service-Katalog** | `dashboard/services.js` ersetzt drei divergierte Service-Listen (`health.js`/`admin.js`/`control.js`) – behebt, dass Hermes im Admin-Systemstatus fehlte |
| **Admin-Tab restrukturiert** | 4 logische Abschnitte: Systemstatus & Steuerung, Sicherung, Protokolle & Diagnose, Benutzerverwaltung |
| **Supabase-Submodul repariert** | Fehlender `.gitmodules`-Eintrag ergänzt, `.git/modules/supabase` via `git submodule absorbgitdirs` initialisiert, Gitlink-Pointer aktualisiert |

### 2026-07 – Teamserver: Hermes Agent, Monitoring, Teams, osTicket, Wissensdatenbank

| Was | Details |
|-----|---------|
| **Rollenhierarchie** | Superadmin / Admin / User via `SUPERADMIN_EMAILS` / `ADMIN_EMAILS`; Rate-Limiting auf allen Control Endpoints |
| **Hermes Agent** | `agent.brain.local` – autonomer KI-Agent (NousResearch, MIT) mit Web-Dashboard + Microsoft-Teams-Gateway; Git Submodul, baut lokal; läuft auf lokalem Ollama; `AUTOSTART_HERMES=true` per Default |
| **Prometheus Monitoring** | Profil `monitoring`: Prometheus, node-exporter, cAdvisor, Pushgateway; Grafana-Datasource auto-provisioniert; Dashboard-Macros zum Starten/Stoppen |
| **SPS Monitoring** | mqtt2prometheus (Profil `monitoring`); OPC-UA als Grafana-Plugin; Konfigurationsvorlagen in `sps-monitoring/` |
| **Teams Bot** | n8n-Arbeitsablauf: Azure Bot Service → Ollama LLM; SSRF-Schutz, JWT Format Check, Prompt-Injection-Mitigation |
| **Grafana → Teams Alerts** | n8n-Arbeitsablauf: Grafana Unified Alerting → Teams Adaptive Cards via Incoming Webhook |
| **Asana Sync** | n8n-Arbeitsablauf: täglich überfällige + bald fällige Tasks als Teams-Nachricht |
| **osTicket KI** | Direkter MySQL-Zugriff: Lösungsvorschläge via Qdrant + Ollama, interne Notiz in Ticket; gelöste Tickets → KB |
| **KB-Arbeitsabläufe** | PDF/Dokument-Ingest + Web-Research-Webhook → Embedding → Qdrant `knowledge_base` + Neo4j (parallel) |
| **Neue Docs** | 21, 23–27: Hermes Agent, Monitoring, SPS, Teams, osTicket, Wissensdatenbank |

### 2026-07 – Ollama: Host-First als Standard

| Was | Details |
|-----|---------|
| `docker-compose.yml` | Ollama Container (`ollama-cpu/gpu/gpu-amd` + Init-Services) aus den Profilen `cpu`/`gpu-nvidia`/`gpu-amd` herausgelöst – neues separates Profil `ollama-docker` |
| `n8n` | `OLLAMA_HOST`: `ollama:11434` → `http://host.docker.internal:11434` |
| `tts-service` | `OLLAMA_HOST`: `http://ollama:11434` → `http://host.docker.internal:11434` |
| Standardverhalten | `python3 start_services.py` startet **keinen** Ollama Container mehr; Ollama läuft nativ auf dem Host |
| Ollama als Container | Nur noch bei explizitem `docker compose --profile ollama-docker up -d` |

### 2026-07 – Hermes Agent

| Was | Details |
|-----|---------|
| `hermes-agent/` | Git Submodul (NousResearch/hermes-agent, MIT) |
| `hermes-gateway` | Autonomer KI-Agent Prozess mit Microsoft Teams Gateway |
| `hermes-dashboard` | Web-UI auf `agent.brain.local` hinter Caddy `forward_auth` |
| `hermes-config/cli-config.yaml` | Lokales Ollama als LLM Provider vorkonfiguriert (`qwen2.5:7b`) |
| `dashboard/macros.json` | Macros „Hermes Agent starten" + „stoppen" |
| `auth-gateway/app.py` | `hermes-gateway` + `hermes-dashboard` in Service-Control registriert |
| `docs/21_hermes_agent.md` | Setup, Teams Registrierung, Modell Konfiguration |

### 2026-07 – Security Hardening: Admin-Rollen, JWT Audience, CSP

| Was | Details |
|-----|---------|
| `auth-gateway/app.py` | Admin Rollenkontrolle: `ADMIN_EMAILS` Env Var + `_require_admin()`; 11 privilegierte `/control/*` Endpoints erfordern Admin Rechte |
| `auth-gateway/app.py` | JWT Audience Verifikation: `aud: "authenticated"` wird geprüft (verhindert Missbrauch von Service Role Tokens) |
| `Caddyfile` | Grafana Admin E-Mail aus hardcoded `wolf@datista.de` → `{$GRAFANA_ADMIN_EMAIL}` (Env Var) |
| `.env.example` | `GRAFANA_ADMIN_EMAIL` und `ADMIN_EMAILS` dokumentiert |
| `Caddyfile` | Content Security Policy für Dashboard Block (script-src CDN Whitelist, connect-src Supabase, frame-ancestors none) |
| `n8n-tool-workflows/stack-service-control.json` | Confused Deputy Fix: Caller JWT wird weitergeleitet statt privilegiertem Workflow Credential; `X-Webhook-Token` als Webhook Auth |
| `docs/05_security_hardening.md` | Admin Rollen, JWT Audience, CSP, Cookie Eigenschaften und bekannte Einschränkungen dokumentiert |
| `docs/15_api_reference.md` | Auth Level (Auth vs. Admin) pro Endpoint ergänzt |

### 2026-06 – Grafana, n8n On-Demand Service Control

| Was | Details |
|-----|---------|
| `grafana` | Grafana in Stack integriert (`grafana.{DOMAIN}`), mit Caddy Routing und Auth Proxy Header |
| `n8n-tool-workflows/stack-service-control.json` | n8n-Arbeitsablauf zum Starten/Stoppen von Stack Services per KI Agent Toolcall |
| `dashboard/macros.json` | Macros erweitert (light-mode, research, rag-mode, save-resources, restart-core) |
| `docs/19_on_demand_services.md` | Neue Doku: Service Control (Dashboard, REST API, n8n Toolcall, Macros) |
| `docs/20_resource_optimization.md` | Neue Doku: Memory Limits, Logging, Disk Maintenance, Custom Image Updates |

---

### 2026-04 – Fix: Docker Compose Projektname

| Was | Details |
|-----|---------|
| `docker-compose.yml` | `name: localai` gesetzt – Projektname ist jetzt fest definiert, kein `-p localai` mehr nötig |

---

### 2026-04 – TTS Service: Voice Cloning & Video Dubbing

| Was | Details |
|-----|---------|
| `tts-service/` | Neuer FastAPI Container (Port 8003) mit [OmniVoice](https://github.com/k2-fsa/OmniVoice) – 600+ Sprachen, RTF 0.025 (40x Echtzeit), Apple Silicon MPS |
| Voice Cloning | Zero-Shot aus 5–15s Referenz Audio; `ref_text` optional (internes Whisper ASR) |
| Voice Design | Stimme via Attributbeschreibung (`"female, british accent"`) ohne Referenz-Audio |
| Video Dubbing | Async Pipeline: ffmpeg → Whisper → Ollama → OmniVoice → ffmpeg; YouTube URL Support |
| `caddy-addon/tts.conf` | Caddy Route `tts.{DOMAIN}` mit `forward_auth` + 600s Timeout für Dubbing |
| `docker-compose.yml` | `tts-service` Block + `TTS_HOSTNAME` in beiden Caddy Instanzen |
| `docs/18_tts_service.md` | Vollständige Doku: Setup, alle 7 Endpunkte, Pipeline, Device Config, Volumes |
| `docs/15_api_reference.md` | TTS Service in API Übersicht ergänzt |

### 2026-03 – OCR Service, Scraping Configurator & API Referenz

| Was | Details |
|-----|---------|
| `ocr-service/` | Neuer FastAPI Container mit TrOCR + Tesseract, 15 Endpunkte, auto Engine Auswahl |
| `caddy-addon/ocr.conf` | Caddy Route für `ocr.{DOMAIN}` mit forward_auth |
| `ocr_storage/` | Input/Output/Temp Verzeichnisse für OCR Verarbeitung |
| `supabase/…/02-04_*.sql` | SQL Schema für `scraped_content` Tabelle |
| `n8n-tool-workflows/scraping-configurator.json` | Konfigurierbarer Scraper: mode (css/llm/auto) × destination (supabase/neo4j/qdrant/sheets/webhook/all) |
| `n8n-tool-workflows/api-health-reference.json` | Live API Referenz Arbeitsablauf mit Health Checks + Endpunkt Katalog |
| `n8n-tool-workflows/ocr-processing-workflow.json` | N8N-Arbeitsablauf für OCR Batch Verarbeitung |
| `docs/14_ocr_service.md` | OCR Service Doku: Setup, alle 15 Endpunkte, Modelle, Storage |
| `docs/15_api_reference.md` | Vollständige API Referenz: 53 Endpunkte über 4 Services |
| `docs/16_scraping_configurator.md` | Scraping Configurator Guide: Modes, Destinations, Beispiele |
| `docs/17_dashboard_changes.md` | Dashboard Architektur: Auth Flow, Tabs, Cards, JS Bridges, Whisper |

### 2026-03 – Authentifizierungssystem: Caddy forward_auth + TOTP/2FA

**Vollständige JWT-basierte Authentifizierung für alle Services**

| Komponente | Was |
|---|-----|
| `auth-gateway/app.py` | Cookie Fallback: liest `sb-access-token` aus Cookie falls kein Authorization Header (Cookie wird seit dem HttpOnly-Umbau serverseitig über `POST /session` gesetzt, siehe Changelog oben) |
| `dashboard/auth.js` | Cookie Management: löst nach Login/Token-Refresh `POST /_auth/session` aus, damit der auth-gateway den `sb-access-token` Cookie auf `.brain.local` setzt |
| `dashboard/auth.js` | TOTP/2FA Flow: nach Passwort-Login automatische MFA Prüfung, TOTP Challenge Schritt |
| `dashboard/auth.js` | 2FA Enrollment: QR Code Anzeige via Supabase `mfa.enroll()`, Bestätigung mit 6-stelligem Code |
| `dashboard/login.html` | Zweistufiges Login Formular (Passwort → TOTP), initialer TOTP Schritt versteckt |
| `dashboard/index.html` | „2FA einrichten"-Button + Modal mit QR Code und Enrollment Flow |
| `Caddyfile` | `(protected)` Snippet: `forward_auth auth-gateway:5001` mit Cookie Weitergabe als Bearer Header; Dashboard ohne `forward_auth` (verhindert Redirect Loop) |
| `Caddyfile` | SearXNG, Qdrant (`qdrant:6333`) als neue geschützte vHosts |
| `Caddyfile` | Crawl4AI Port korrigiert: `8082` → `11235` |
| `docker-compose.yml` | auth-gateway: Profil `public` → `auth` (wird via `--profile auth` aktiviert) |
| `start_services.py` | `--environment public` ist neuer Standard; `--profile auth` + `public.supabase.yml` automatisch bei `--environment public` |
| `docker-compose.override.public.supabase.yml` | GoTrue TOTP aktiviert: `GOTRUE_MFA_ENABLED=true`, `GOTRUE_MFA_TOTP_ENABLED=true` |
| `.env.example` | `QDRANT_HOSTNAME` ergänzt; Produktions Beispiel auf `yourdomain.com` |

### 2026-03 – Python NLP/Dokumentenservice v2.0

**`python-nlp-service/` – OCR + multilingual NER**

| Komponente | Alt | Neu |
|-----------|-----|-------|
| Funktion | Nur deutsches NER | NER (DE+EN) + OCR + PDF Extraktion |
| SpaCy Modelle | `de_core_news_md` | `de_core_news_md` + `en_core_web_md` |
| OCR | — | Via Ollama `glm-ocr` (konfigurierbar via `OCR_MODEL`) |
| PDF Extraktion | — | PyMuPDF (direkt + OCR Fallback für gescannte PDFs) |
| Neuer Haupt Endpunkt | — | `POST /document/analyze` (Text + Entities in einem Call) |
| Compat Endpoints | — | `/pdf/extract`, `/pdf/analyze-type`, `/pdf/to-png-smart` |
| RAM Limit | 1 GB | 1.5 GB (zwei SpaCy Modelle) |
| Neue Env Variablen | — | `OLLAMA_HOST`, `OCR_MODEL` |
| extra_hosts | — | `host.docker.internal:host-gateway` (Linux Kompatibilität) |
| n8n depends_on | auskommentiert | aktiv (`service_healthy`) |

---

### 2026-02 – Abhängigkeitsaktualisierungen

**Python Pakete auf neueste aktualisiert (CVE-clean, verifiziert via OSV.dev)**

| Paket | Alt | Neu | Dateien |
|-------|-----|-----|---------|
| `flask` | 3.1.1 | **3.1.3** | auth-gateway, python-nlp-service |
| `gunicorn` | 23.0.0 | **25.1.0** | auth-gateway, python-nlp-service |
| `werkzeug` | 3.1.5 | **3.1.6** | python-nlp-service |
| `requests` | 2.32.4 | **2.32.5** | python-nlp-service |
| `spacy` | 3.8.3 | **3.8.11** | python-nlp-service |
| `numpy` | 2.2.3 | **2.4.2** | python-nlp-service |
| `pandas` | 2.2.3 | **3.0.1** ⚠️ Major | python-nlp-service |
| `textblob` | 0.18.0 | **0.19.0** | python-nlp-service |
| `python-json-logger` | 3.0.0 | **4.0.0** ⚠️ Major | python-nlp-service |

**Supabase Submodul Pointer aktualisiert**

| Komponente | Alt | Neu |
|-----------|-----|-------|
| Pointer | `169e3d9` | `571e060` |
| supabase-studio | 2025.11.10 | **2026.02.16** |
| gotrue (auth) | v2.182.1 | **v2.186.0** |
| postgrest | v13.0.7 | **v14.5** ⚠️ Major |
| realtime | v2.63.0 | **v2.76.5** |

---

### 2026-02 – Docker Compose & Infrastruktur

**`docker-compose.yml` – Bug Fixes & Verbesserungen**

| Prio | Service | Was | Fix |
|------|---------|-----|-----|
| 🔴 Bug | `python-nlp-service` | Healthcheck testete Port `5050` statt `5000` – Container wurde permanent als `unhealthy` markiert | Port korrigiert |
| 🟠 Stability | `open-webui` | Image Tag `:main` (Development Branch, instabil) | → `:latest` (überholt, seit 2026-11 exakt gepinnt) |
| 🟠 Correctness | `python-nlp-service` | `FLASK_ENV=production` seit Flask 2.2 deprecated, bei Gunicorn Betrieb wirkungslos | Variable entfernt |
| 🟠 Ops | `python-nlp-service`, `neo4j` | `restart: always` startet Container auch nach manuellem `docker stop` neu | → `unless-stopped` |
| 🟠 Ops | `n8n`, `python-nlp-service`, `open-webui`, `neo4j` | Keine Log Rotation konfiguriert, Logs können unkontrolliert wachsen | `json-file` Driver mit `max-size: 10m / max-file: 3` |
| 🟡 Usability | `neo4j` | Kein `container_name`, kein Healthcheck | `container_name: neo4j` + HTTP Check auf Port 7474 |

**`start_services.py` – Bug Fix**

| Prio | Funktion | Was | Fix |
|------|----------|-----|-----|
| 🔴 Bug | `check_and_fix_docker_compose_for_searxng()` | SearXNG `cap_drop`-Fix suchte nach `"cap_drop: - ALL"` als Einzeiler, YAML enthält aber Multi-Line Format (`cap_drop:\n  - ALL`) → Bedingung war immer `False`, SearXNG konnte beim ersten Start fehlschlagen | Suchstring auf korrektes Multi Line Format geändert, eindeutig über nachfolgendes `cap_add: CHOWN` |

---

### 2026-02 – Python NLP Service

**`python-nlp-service/` – Versions Update & Optimierung**

| Component | Before | After | Hinweis |
|-----------|--------|-------|---------|
| Python | 3.11 | **3.12** | |
| SpaCy model | `de_core_news_sm` (~13 MB) | **`de_core_news_md`** (~43 MB) | Bessere NER Qualität, kein GPU nötig |
| NumPy | 1.26.x | **2.2.x** | Breaking Changes zu 1.x; SpaCy 3.8.x und pandas 2.2.x kompatibel |
| Flask | 3.0.0 | **3.1.0** | |
| Gunicorn | 21.2.0 | **23.0.0** | |
| spaCy | 3.7.5 | **3.8.3** | |
| pandas | 2.1.4 | **2.2.3** | |
| requests | 2.31.0 | **2.32.3** | |
| python-json-logger | 2.0.7 | **3.0.0** | |
| Dockerfile Struktur | Site packages direkt kopiert | **Virtual Environment** `/opt/venv` | Saubere Isolation, kein versehentliches Mitkopieren von Build Tools |
| Sicherheit | Root User, keine feste UID | **Non-root UID 1001** | |
| Monitoring | Kein Docker HEALTHCHECK | **`HEALTHCHECK`** über `/health` Endpoint | |
| OCR | — | Über **Ollama** (nicht in diesem Container) | |

---

### 2026-02 – Security Hardening & Verbesserungen

**`auth-gateway/` – Vollständige Sicherheitshärtung**

| Prio | Komponente | Was | Fix |
|------|-----------|-----|-----|
| 🔴 Sicherheit | `Dockerfile` | Root User, kein multi-stage Build, keine feste UID, kein `HEALTHCHECK`, kein `apt-get upgrade` | Multi stage Build + Virtual Environment `/opt/venv`, Non-root UID 1002, `HEALTHCHECK`, `apt-get upgrade` |
| 🔴 Sicherheit | `app.py` | Sensitive Token Daten wurden in Logs geschrieben → potenzielle Credential Exposition | Sensible Daten vollständig entfernt; generische Warning Message |
| 🟠 Stability | `app.py` | Kein `/health` Endpoint → `HEALTHCHECK` und Monitoring nicht möglich | `/health`-Endpoint hinzugefügt |
| 🟠 Versions | `requirements.txt` | `flask==3.0.0`, `gunicorn==21.2.0`, `supabase==2.4.2` (>1 Jahr alt) | `flask==3.1.0`, `gunicorn==23.0.0`, `supabase==2.28.0` |

**`python-nlp-service/app.py` – DoS Schutz**

| Prio | Komponente | Was | Fix |
|------|-----------|-----|-----|
| 🔴 Sicherheit | `/process` Endpoint | Keine Eingabegrößenbeschränkung → beliebig große Texte möglich (DoS) | Maximale Eingabegröße begrenzt; HTTP 413 bei Überschreitung |

**`Caddyfile` – Security Headers**

| Prio | Komponente | Was | Fix |
|------|-----------|-----|-----|
| 🟠 Sicherheit | Alle vHosts | Keine Security Headers konfiguriert | `(security_headers)` Snippet mit HSTS, X-Content-Type Options, X Frame Options, Referrer Policy, Permissions Policy, `-Server` in allen aktiven vHosts |

**`backup.sh` – .env Backup**

| Prio | Komponente | Was | Fix |
|------|-----------|-----|-----|
| 🟠 Ops | `.env` | Konfigurationsdatei mit Secrets wurde nicht gesichert | `.env` wird mit `chmod 600` ins Backup Verzeichnis kopiert |

**`docker-compose.yml` – crawl4ai Ressourcenlimits**

| Prio | Komponente | Was | Fix |
|------|-----------|-----|-----|
| 🟠 Stability | `crawl4ai` | Keine Ressourcen Limits, kein Healthcheck | Memory Limit 3 GB (Reservation 512 MB), `HEALTHCHECK` auf `/health` Port 11235 |

**`dashboard/index.html` – CDN Subresource Integrity**

| Prio | Komponente | Was | Fix |
|------|-----------|-----|-----|
| 🟡 Supply Chain | `supabase-js` CDN | Floating Tag `@2` ohne SRI Hash → CDN Kompromittierung möglich | Gepinnte Version `@2.97.0` + `integrity="sha384-..."` + `crossorigin="anonymous"` |

**CVE Scan (`pip-audit` + OSV.dev) – Versionskorrektur**

| CVE/GHSA | Paket | Betroffen | Fix | Beschreibung |
|----------|-------|-----------|-----|--------------|
| CVE-2025-47278 | `flask` | 3.1.0 | **3.1.1** | Signing Key Reihenfolge invertiert → falscher Key zum Signieren verwendet |
| GHSA-9hjg-9r4m-mvj7 | `requests` | 2.32.3 | **2.32.4** | `.netrc` Credentials Leak über manipulierte URLs |
| GHSA-hgf8-39gv-g3f2 | `werkzeug` | 3.1.3 | **3.1.5** | `safe_join()` erlaubt Windows Sondergerätenamen |
| GHSA-87hc-h4r5-73f7 | `werkzeug` | 3.1.3 | **3.1.5** | `safe_join()` erlaubt Sondergerätenamen mit zusammengesetzten Endungen |

Fixes angewendet in `auth-gateway/requirements.txt` und `python-nlp-service/requirements.txt`.

---

### 2026-03 – Upstream Sync (coleam00/local-ai-packaged)

Selektive Übernahme von 13 Upstream Commits. Unsere Ergänzungen (auth-gateway, dashboard, docs, python-nlp-service) bleiben vollständig erhalten.

| Was | Upstream Commit | Übernahme |
|---|---|---------|
| `n8n-import` Service entfernt | `48c186a`, `8d02114` | ✅ Service + `depends_on` Eintrag entfernt |
| n8n `LocalFileTrigger` + `ExecuteCommand` aktivierbar | `ce882b7` | ✅ `NODES_EXCLUDE` Kommentar in x-n8n hinzugefügt |
| Neue Supabase Storage Env Vars | `57c194a` | ✅ In `.env.example` ergänzt |
| Neue n8n Workflow Dateien (V1/V2/V3 RAG Agent) | `5c55af2` | ✅ In `n8n/backup/workflows/` kopiert |
| shared Volume Pfad: `:/home/node/.n8n-files/shared` → `:/data/shared` | `8d02114` | ✅ Übernommen |
| Caddy Hostnames ohne `${DOMAIN}` | — | ⏭️ Nicht übernommen (unser Setup nutzt `${DOMAIN}`) |
| `open-webui:latest` → `:main` | — | ⏭️ Nicht übernommen (`:latest` stabiler; überholt, seit 2026-11 exakt gepinnt) |
| `crawl4ai` entfernt | — | ⏭️ Nicht übernommen (Teil unseres Stacks) |
| `neo4j` restart: always, kein Healthcheck | — | ⏭️ Nicht übernommen (unser Healthcheck behalten) |
