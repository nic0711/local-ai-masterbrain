# Deutsch 🇩🇪  [-> English 🇬🇧](#english)

## Self-hosted AI Masterbrain 🚀

**Lokale KI-Entwicklungs-Umgebung** mit n8n, Supabase, Ollama, WebUI, Crawl4AI, Qdrant und mehr.  
Ideal zum Erstellen eigener RAG-Arbeitsabläufe (RAG workflows), Daten-Agenten und sicherer KI-Experimente – lokal oder in der Cloud.

Dies ist Wolf's Version mit einigen Verbesserungen und dem Hinzufügen von Crawl4ai, NLP-Container und Dashboard mit Authentifizierung.  

Außerdem werden die lokalen RAG-KI-Agent-Arbeitsabläufe aus dem Video (von Cole) automatisch in Ihrer n8n-Instanz vorhanden sein, wenn Sie diese Einrichtung anstelle der Basisversion verwenden, die von n8n bereitgestellt wird!

---

## Praxisbeispiele: So arbeiten die Services zusammen

### Beispiel 1 – Support-Ticket wird automatisch gelöst

Ein Mitarbeiter öffnet ein Ticket in **osTicket**: *„VPN bricht nach 10 Minuten ab."*

```
osTicket (MySQL)
  → n8n (alle 10 min): Ticket auslesen
  → Ollama (nomic-embed-text): Ticket-Text in Vektor umwandeln
  → Qdrant: Ähnliche gelöste Tickets suchen
      ↳ Treffer: "VPN Timeout – MTU-Problem" (Score 0.89)
  → Ollama (qwen2.5:7b): Lösungsvorschlag generieren
      Kontext: Ticket-Text + gefundene Lösung aus Qdrant
  → osTicket API: Interne Notiz mit Lösungsvorschlag posten
  → Teams (Incoming Webhook): Benachrichtigung an Support-Kanal
```

Der Support-Mitarbeiter findet bereits beim Öffnen des Tickets einen konkreten Lösungsvorschlag mit Schritt-für-Schritt-Anleitung – generiert aus der eigenen Wissensdatenbank gelöster Tickets. Neue gelöste Tickets fließen täglich automatisch zurück in Qdrant und Neo4j.

---

### Beispiel 2 – Hermes Agent beantwortet Team-Anfragen direkt in Teams

Ein Teammitglied erwähnt **@Hermes** in einem Microsoft-Teams-Kanal: *„Fasse die aktuellen Neuerungen im Kubernetes-Netzwerkmodell zusammen."*

```
Microsoft Teams (@Hermes erwähnt)
  → hermes-gateway (Teams-Gateway, Azure Bot Service)
  → Ollama (host.docker.internal:11434, qwen2.5:7b)
  → Web-Tool (web_search / web_extract): recherchiert externe Quellen
  → Antwort direkt im Teams-Thread
```

Hermes läuft komplett auf dem lokalen Ollama-Modell und antwortet ohne Umweg über einen separaten Web-Client. Für die dauerhafte Ablage von Rechercheergebnissen in die zentrale Wissensdatenbank (Qdrant + Neo4j) sind weiterhin die dedizierten n8n-KB-Workflows zuständig, siehe [`docs/27_knowledge_base.md`](docs/27_knowledge_base.md).

---

**WICHTIG**: Supabase hat einige Umgebungsvariablen aktualisiert, sodass Sie möglicherweise neue Standardwerte für Ihre `.env` hinzufügen müssen (wie in meiner ` .env.example`, falls Sie dieses Projekt bereits betreiben und nur neue Änderungen ziehen). Insbesondere müssen Sie `"POOLER_DB_POOL_SIZE=5"` zu Ihrer `.env` hinzufügen. Dies ist erforderlich, wenn Sie das Paket vor dem 14. Juni laufen hatten.

**WICHTIG**: `AUTOSTART_HERMES=true` ist Standard, aber Hermes verweigert den Bind auf `0.0.0.0`, solange kein Auth-Provider konfiguriert ist. Setzen Sie in Ihrer `.env` zwingend `HERMES_DASHBOARD_PASSWORD` (`openssl rand -hex 16`) und `HERMES_DASHBOARD_AUTH_SECRET` (`openssl rand -hex 32`) – ohne diese beiden Werte bleibt `hermes-dashboard` trotz Autostart unerreichbar. Details: [`docs/21_hermes_agent.md`](docs/21_hermes_agent.md).

## Wichtige Links

- [Original Local AI Starter Kit](https://github.com/n8n-io/self-hosted-ai-starter-kit) vom n8n-Team
- [Basiert auf der Local AI Packaged](https://github.com/coleam00/local-ai-packaged) von coleam00 & Team
- Laden Sie Coles N8N + OpenWebUI-Integration [direkt auf der Open WebUI-Seite herunter.](https://openwebui.com/f/coleam/n8n_pipe/) (weitere Anweisungen unten)

Kuratiert von <https://github.com/n8n-io> und <https://github.com/coleam00>, kombiniert es die selbst gehostete n8n-Plattform mit einer kuratierten Liste kompatibler KI-Produkte und -Komponenten, um schnell den Einstieg beim Erstellen von selbstgehosteten KI-Arbeitsabläufen zu ermöglichen.

---

### Was ist enthalten

✅ [**Selbst gehoste n8n**](https://n8n.io/) – Low-code-Plattform mit über 400 Integrationen und fortschrittlichen AI-Komponenten
✅ **[Dashboard mit Auth]** – Übersichtsseite aller Services mit JWT-basierter Authentifizierung (E-Mail + Passwort + optionales TOTP/2FA), geschützt durch Caddy `forward_auth`
✅ [**Supabase**](https://supabase.com/) – Open-Source-Datenbank als Service – am weitesten verbreitete Datenbank für KI-Agenten
✅ [**Ollama**](https://ollama.com/) – Cross-platform LLM-Plattform zum Installieren und Ausführen der neuesten lokalen LLMs
✅ [**Open WebUI**](https://openwebui.com/) – ChatGPT-artige Schnittstelle zur privaten Interaktion mit Ihren lokalen Modellen und N8N-Agenten
✅ [**Hermes Agent**](https://github.com/NousResearch/hermes-agent) – Autonomer KI-Agent (NousResearch, MIT) mit Web-Dashboard und Microsoft Teams Gateway; läuft auf lokalem Ollama, startet standardmäßig automatisch mit dem Stack
✅ [**Flowise**](https://flowiseai.com/) – No-/Low-Code KI-Agent Builder, der sehr gut zu n8n passt
✅ [**Crawl4ai**](https://crawl4ai.com/) - Scraping / Crawling für LLM-Nutzung oder Datenaggregation, Screenshots usw. 
✅ [**TTS Service / Voice Cloning / Video Dubbing**] – Lokaler Text-zu-Sprache-Container mit [OmniVoice](https://github.com/k2-fsa/OmniVoice) (600+ Sprachen, RTF 0.025). Zero-Shot Voice Cloning aus 5–15s Referenz-Audio, Voice Design via Attributbeschreibung (Geschlecht, Akzent, Tonlage), asynchrones Video-Dubbing mit Whisper-Transkription und Ollama-Übersetzung.
✅ [**Python NLP / Document Service**] – Produktionsreifer Dokumentenverarbeitungscontainer mit Flask/Gunicorn. Extrahiert Text aus PDFs und Bildern, führt OCR via **Ollama glm-ocr** durch (kein lokaler Tesseract erforderlich) und führt Named Entity Recognition (NER) auf Deutsch und Englisch via SpaCy durch. Bietet eine einzelne `/document/analyze`-Endpunkt, der Text + Entitäten in einem Aufruf zurückgibt – ideal als Vorverarbeitungspipeline für Neo4j Knowledge Graphs und n8n-Arbeitsabläufe.
✅ [**Qdrant**](https://qdrant.tech/) - Open Source, High Performance Vector Store mit einer umfassenden API. Obwohl Sie Supabase für RAG verwenden können, wurde dies beibehalten (im Gegensatz zu Postgres), da es schneller als Supabase ist und manchmal die bessere Option darstellt.
✅ [**Neo4j**](https://neo4j.com/) - Knowledge Graph Engine, die Tools wie GraphRAG, LightRAG und Graphiti antreibt 
✅ [**SearXNG**](https://searxng.org/) - Open Source, kostenloser Internet-Metasuchmotor, der Ergebnisse von bis zu 229 Suchdiensten aggregiert. Benutzer werden weder verfolgt noch profiliert, daher die Passform zum lokalen KI-Paket.
✅ [**Caddy**](https://caddyserver.com/) – Managed HTTPS/TLS für benutzerdefinierte Domains
✅ [**Grafana**](https://grafana.com/) - Monitoring & Dashboards für Stack-Metriken, Container-Health und Logs
✅ [**Uptime Kuma**](https://github.com/louislam/uptime-kuma) – Self-hosted Uptime-Monitoring mit Status-Page (`status.brain.local`), Benachrichtigungen und Maintenance-Windows; eine der wenigen Ausnahmen ohne Caddy `forward_auth`
✅ [**Prometheus-Stack**] – Optionales Monitoring mit Prometheus, node-exporter, cAdvisor und Pushgateway; Grafana-Datasource automatisch bereitgestellt; SPS-Exporter für MQTT + Modbus + OPC-UA
✅ **[Teams-Bot + Asana]** - n8n-Arbeitsabläufe: Azure Bot Service → Ollama LLM-Antworten in Teams; Grafana-Alerts als Adaptive Cards; täglicher Asana-Task-Bericht
✅ [**osTicket KI-Integration**] – n8n liest direkt aus der osTicket-MySQL-Datenbank, generiert Lösungsvorschläge via Ollama + Qdrant-Ähnlichkeitssuche und postet interne Notizen; gelöste Tickets fließen automatisch in Neo4j + Qdrant
✅ [**Wissensdatenbank (KB)**] – Zwei Ingest-Arbeitsabläufe: PDF/Dokumente oder Web-Research per Webhook → Embedding + NER → Qdrant (`knowledge_base`) + Neo4j parallel indiziert
✅ [**Langfuse**](https://langfuse.com/) - Open Source LLM Engineering Plattform für Agent-Observability

---

## 🌟 Features

- ✅ Lokaler oder servergehosteter Ollama und/oder öffentliche LLMs
- ✅ Hermes Agent: autonomer KI-Agent mit Teams-Gateway, Web-Dashboard, Autostart mit dem Stack, steuerbar per Dashboard-Macro
- ✅ JWT-Authentifizierung via Caddy `forward_auth` – alle Services geschützt
- ✅ TOTP/2FA über Supabase GoTrue (kein extra Container)
- ✅ Supabase mit Vector Store & Authentifizierung
- ✅ Crawl4AI, Qdrant, Neo4j, Langfuse, Python NLP/Dokumentenservice (OCR + NER, DE+EN), MinIO, Open WebUI, ...
- ✅ TTS Service: Voice Cloning (OmniVoice, 600+ Sprachen), Video-Dubbing (Whisper + Ollama + ffmpeg), Apple Silicon MPS
- ✅ Grafana Monitoring mit Caddy-Routing + Auth-Proxy-Header
- ✅ On-Demand Service Control: Dashboard Admin-Tab, REST API, n8n Toolcall
- ✅ Ollama standardmäßig nativ auf dem Host – kein Ollama Container beim normalen Start
- ✅ Prometheus Monitoring: node-exporter, cAdvisor, Pushgateway, SPS Exporter (MQTT/Modbus/OPC-UA)
- ✅ Teams-Bot + Asana: n8n-Arbeitsabläufe für Chat, Grafana-Alerts, Task-Berichte
- ✅ osTicket KI: direkter MySQL-Zugriff, Lösungsvorschläge via Qdrant + Ollama, auto KB-Sync
- ✅ Wissensdatenbank: PDF/Web-Research → Qdrant + Neo4j; Tickets fließen automatisch ein
- ✅ Superadmin/Admin/User Rollenhierarchie mit Rate-Limiting auf allen Control Endpoints
- ✅ Automatisierter Start & Cleanup via `start_services.py`

---

Bevor Sie beginnen, stellen Sie sicher, dass die folgende Software installiert ist:

- [Python](https://www.python.org/downloads/) - Erforderlich zum Ausführen des Setup-Skripts
- [Git/GitHub Desktop](https://desktop.github.com/) - Für einfache Repositoryverwaltung
- [Docker/Docker Desktop](https://www.docker.com/products/docker-desktop/) - Erforderlich zum Ausführen aller Dienste

---

## 🔧 Quickstart

```bash
git clone -b stable https://github.com/nic0711/local-ai-masterbrain
cd local-ai-masterbrain
cp .env.example .env              # Secrets eintragen!
python3 start_services.py         # Standard: Ollama läuft lokal auf dem Host
# python3 start_services.py --profile gpu-nvidia     # Nvidia GPU (ohne Ollama Container)
# docker compose --profile ollama-docker up -d       # Ollama als Docker-Container
```

> Weitere Details zu `--profile` und `--environment`: [docs/03_start_services.md](docs/03_start_services.md)

👉 Dashboard: https://brain.local  
👉 n8n: https://n8n.brain.local  
👉 Open WebUI: https://webui.brain.local  

---

## 📚 Dokumentation

| Thema                    | Datei                                    |
|--------------------------|------------------------------------------|
| Installation             | [01_installation.md](docs/01_installation.md) |
| Konfiguration (.env)     | [02_configuration.md](docs/02_configuration.md) |
| Startskript (Details)    | [03_start_services.md](docs/03_start_services.md) |
| Cloud Deployment         | [04_cloud_deployment.md](docs/04_cloud_deployment.md) |
| Security Hardening       | [05_security_hardening.md](docs/05_security_hardening.md) |
| Nutzung: n8n & WebUI     | [06_usage_n8n_openwebui.md](docs/06_usage_n8n_openwebui.md) |
| Fehlerbehebung          | [07_troubleshooting.md](docs/07_troubleshooting.md) |
| Backup & Recovery        | [08_backup_and_recovery.md](docs/08_backup_and_recovery.md) |
| FAQ & Tipps              | [09_faq.md](docs/09_faq.md) |
| Python NLP/Dokumentenservice | [10_python_nlp_service.md](docs/10_python_nlp_service.md) |
| Obsidian-Integration     | [11_obsidian_integration.md](docs/11_obsidian_integration.md) |
| Monitoring (Uptime Kuma) | [12_monitoring.md](docs/12_monitoring.md) |
| GraphRAG (Neo4j Knowledge Graph) | [13_graphrag.md](docs/13_graphrag.md) |
| Links & Ressourcen       | [tips_links.md](docs/tips_links.md) |
| OCR Service              | [14_ocr_service.md](docs/14_ocr_service.md) |
| API Referenz             | [15_api_reference.md](docs/15_api_reference.md) |
| Scraping Configurator    | [16_scraping_configurator.md](docs/16_scraping_configurator.md) |
| Dashboard Architektur    | [17_dashboard_changes.md](docs/17_dashboard_changes.md) |
| TTS / Voice Cloning / Dubbing | [18_tts_service.md](docs/18_tts_service.md) |
| On-Demand Services (Service Control) | [19_on_demand_services.md](docs/19_on_demand_services.md) |
| Ressourcen-Optimierung (Memory, Logging) | [20_resource_optimization.md](docs/20_resource_optimization.md) |
| Hermes Agent (KI-Agent, Teams, Web-UI) | [21_hermes_agent.md](docs/21_hermes_agent.md) |
| Monitoring (Prometheus, cAdvisor, Pushgateway) | [23_monitoring.md](docs/23_monitoring.md) |
| SPS-Monitoring (OPC-UA, MQTT, Modbus) | [24_sps_monitoring.md](docs/24_sps_monitoring.md) |
| Teams Bot + Asana-Integration | [25_teams_bot.md](docs/25_teams_bot.md) |
| osTicket KI Integration  | [26_osticket_ki.md](docs/26_osticket_ki.md) |
| Wissensdatenbank (KB-Arbeitsabläufe) | [27_knowledge_base.md](docs/27_knowledge_base.md) |

---

## 📋 Changelog

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
| **SPS Monitoring** | mqtt2prometheus + modbus-exporter (Profil `monitoring`); OPC-UA als Grafana-Plugin; Konfigurationsvorlagen in `sps-monitoring/` |
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
| `dashboard/macros.json` | Macros erweitert (light-mode, research, rag-mode, langfuse-start, save-resources, restart-core) |
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
| `docs/15_api_reference.md` | Vollständige API Referenz: 43 Endpunkte über 3 Services |
| `docs/16_scraping_configurator.md` | Scraping Configurator Guide: Modes, Destinations, Beispiele |
| `docs/17_dashboard_changes.md` | Dashboard Architektur: Auth Flow, Tabs, Cards, JS Bridges, Whisper |

### 2026-03 – Authentifizierungssystem: Caddy forward_auth + TOTP/2FA

**Vollständige JWT-basierte Authentifizierung für alle Services**

| Komponente | Was |
|---|-----|
| `auth-gateway/app.py` | Cookie Fallback: liest `sb-access-token` aus Cookie falls kein Authorization Header |
| `dashboard/auth.js` | Cookie Management: setzt JWT nach Login als `sb-access-token` Cookie auf `.brain.local`; `onAuthStateChange` hält Cookie bei Token Refresh aktuell |
| `dashboard/auth.js` | TOTP/2FA Flow: nach Passwort-Login automatische MFA Prüfung, TOTP Challenge Schritt |
| `dashboard/auth.js` | 2FA Enrollment: QR Code Anzeige via Supabase `mfa.enroll()`, Bestätigung mit 6-stelligem Code |
| `dashboard/login.html` | Zweistufiges Login Formular (Passwort → TOTP), initialer TOTP Schritt versteckt |
| `dashboard/index.html` | „2FA einrichten"-Button + Modal mit QR Code und Enrollment Flow |
| `Caddyfile` | `(protected)` Snippet: `forward_auth auth-gateway:5001` mit Cookie Weitergabe als Bearer Header; Dashboard ohne `forward_auth` (verhindert Redirect Loop) |
| `Caddyfile` | SearXNG, Qdrant (`qdrant:6333`), Minio (`minio:9001`) als neue geschützte vHosts |
| `Caddyfile` | Crawl4AI Port korrigiert: `8082` → `11235` |
| `docker-compose.yml` | auth-gateway: Profil `public` → `auth` (wird via `--profile auth` aktiviert) |
| `start_services.py` | `--environment public` ist neuer Standard; `--profile auth` + `public.supabase.yml` automatisch bei `--environment public` |
| `docker-compose.override.public.supabase.yml` | GoTrue TOTP aktiviert: `GOTRUE_MFA_ENABLED=true`, `GOTRUE_MFA_TOTP_ENABLED=true` |
| `.env.example` | `QDRANT_HOSTNAME`, `MINIO_HOSTNAME` ergänzt; Produktions Beispiel auf `yourdomain.com` |

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
| 🟠 Stability | `open-webui` | Image Tag `:main` (Development Branch, instabil) | → `:latest` |
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
| `LANGFUSE_ENCRYPTION_KEY` → `ENCRYPTION_KEY` | — | ✅ In `docker-compose.yml` + `.env.example` |
| Caddy Hostnames ohne `${DOMAIN}` | — | ⏭️ Nicht übernommen (unser Setup nutzt `${DOMAIN}`) |
| `open-webui:latest` → `:main` | — | ⏭️ Nicht übernommen (`:latest` stabiler) |
| `crawl4ai` entfernt | — | ⏭️ Nicht übernommen (Teil unseres Stacks) |
| `neo4j` restart: always, kein Healthcheck | — | ⏭️ Nicht übernommen (unser Healthcheck behalten) |

---

📜 Lizenz: Apache 2.0 – siehe [LICENSE](LICENSE)

---
<a id="english"></a>
# English 🇬🇧

## Self-hosted AI Masterbrain 🚀

**Local AI development stack** with n8n, Supabase, Ollama, WebUI, Crawl4AI, Qdrant, and more.  
Ideal for building your own RAG workflows, data agents, and secure AI experiments – locally or in the cloud.

This is Wolf's version with a couple of improvements and the addition of Crawl4ai, NLP-Container and Dashboard with Auth.  

Also, the local RAG AI Agent workflows from the video (by Cole) will be automatically in your n8n instance if you use this setup instead of the base one provided by n8n!

---

## Practical Examples: How Services Work Together

### Example 1 – Support Ticket Solved Automatically

An employee opens a ticket in **osTicket**: *"VPN disconnects after 10 minutes."*

```
osTicket (MySQL)
  → n8n (every 10 min): Read ticket
  → Ollama (nomic-embed-text): Convert ticket text to vector
  → Qdrant: Search for similar resolved tickets
      ↳ Match: "VPN Timeout – MTU Problem" (Score 0.89)
  → Ollama (qwen2.5:7b): Generate solution suggestion
      Context: Ticket text + found solution from Qdrant
  → osTicket API: Post internal note with solution suggestion
  → Teams (Incoming Webhook): Notify support channel
```

The support agent finds a concrete step-by-step solution suggestion already when opening the ticket – generated from their own knowledge base of resolved tickets. Newly resolved tickets automatically flow back into Qdrant and Neo4j daily.

---

### Example 2 – Hermes Agent Answers Team Requests Directly in Teams

A team member mentions **@Hermes** in a Microsoft Teams channel: *"Summarize the latest changes to the Kubernetes network model."*

```
Microsoft Teams (@Hermes mentioned)
  → hermes-gateway (Teams gateway, Azure Bot Service)
  → Ollama (host.docker.internal:11434, qwen2.5:7b)
  → Web tool (web_search / web_extract): researches external sources
  → Reply posted directly in the Teams thread
```

Hermes runs entirely on the local Ollama model and answers without a separate web client. Persisting research results into the central knowledge base (Qdrant + Neo4j) is still handled by the dedicated n8n KB workflows, see [`docs/27_knowledge_base.md`](docs/27_knowledge_base.md).

---

**IMPORTANT**: Supabase has updated several environment variables so you may have to add some new default values in your `.env` that I have in my `.env.example` if you already had this project running and are just pulling new changes. Specifically, you need to add `"POOLER_DB_POOL_SIZE=5"` to your `.env`. This is required if you had the package running before June 14th.

**IMPORTANT**: `AUTOSTART_HERMES=true` is the default, but Hermes refuses to bind to `0.0.0.0` until an auth provider is configured. You must set `HERMES_DASHBOARD_PASSWORD` (`openssl rand -hex 16`) and `HERMES_DASHBOARD_AUTH_SECRET` (`openssl rand -hex 32`) in your `.env` – without these two values, `hermes-dashboard` stays unreachable despite autostart. Details: [`docs/21_hermes_agent.md`](docs/21_hermes_agent.md).

## Important Links

- [Original Local AI Starter Kit](https://github.com/n8n-io/self-hosted-ai-starter-kit) by the n8n team
- [Based on the Local AI Packaged](https://github.com/coleam00/local-ai-packaged) by coleam00 & team
- Download Cole's N8N + OpenWebUI integration [directly on the Open WebUI site.](https://openwebui.com/f/coleam/n8n_pipe/) (more instructions below)

Curated by <https://github.com/n8n-io> and <https://github.com/coleam00>, it combines the self-hosted n8n platform with a curated list of compatible AI products and components to quickly get started with building self-hosted AI workflows.

---

### What's Included

✅ [**Self-hosted n8n**](https://n8n.io/) - Low-code platform with over 400 integrations and advanced AI components
✅ **[Dashboard with Auth]** – Overview page of all services with JWT-based authentication (Email + Password + optional TOTP/2FA), protected by Caddy `forward_auth`
✅ [**Supabase**](https://supabase.com/) - Open source database as a service - most widely used database for AI agents
✅ [**Ollama**](https://ollama.com/) - Cross-platform LLM platform to install and run the latest local LLMs
✅ [**Open WebUI**](https://openwebui.com/) - ChatGPT-like interface to privately interact with your local models and N8N agents
✅ [**Hermes Agent**](https://github.com/NousResearch/hermes-agent) - Autonomous AI agent (NousResearch, MIT) with web dashboard and Microsoft Teams gateway; runs on local Ollama, starts automatically with the stack by default
✅ [**Flowise**](https://flowiseai.com/) - No/low code AI agent builder that pairs very well with n8n
✅ [**Crawl4ai**](https://crawl4ai.com/) - scraping / crawling for LLM usage or data aggregation, screenshots, etc. 
✅ [**TTS Service / Voice Cloning / Video Dubbing**] - Local Text-to-Speech container with [OmniVoice](https://github.com/k2-fsa/OmniVoice) (600+ languages, RTF 0.025). Zero-Shot Voice Cloning from 5–15s reference audio, voice design via attribute description (gender, accent, tone), asynchronous video dubbing with Whisper transcription and Ollama translation.
✅ [**Python NLP / Document Service**] - Production-ready document processing container with Flask/Gunicorn. Extracts text from PDFs and images, runs OCR via **Ollama glm-ocr** (no local Tesseract needed), and performs Named Entity Recognition (NER) in German and English via SpaCy. Provides a single `/document/analyze` endpoint that returns text + entities in one call – ideal as preprocessing pipeline for Neo4j Knowledge Graphs and n8n workflows.
✅ [**Qdrant**](https://qdrant.tech/) - Open source, high performance vector store with comprehensive API. Even though you can use Supabase for RAG, this was kept unlike Postgres since it's faster than Supabase so sometimes is the better option.
✅ [**Neo4j**](https://neo4j.com/) - Knowledge graph engine that powers tools like GraphRAG, LightRAG, and Graphiti 
✅ [**SearXNG**](https://searxng.org/) - Open source, free internet metasearch engine which aggregates results from up to 229 search services. Users are neither tracked nor profiled, hence the fit with the local AI package.
✅ [**Caddy**](https://caddyserver.com/) - Managed HTTPS/TLS for custom domains
✅ [**Grafana**](https://grafana.com/) - Monitoring & Dashboards for stack metrics, container health and logs
✅ [**Uptime Kuma**](https://github.com/louislam/uptime-kuma) - Self-hosted uptime monitoring with status page (`status.brain.local`), notifications and maintenance windows; one of the few exceptions without Caddy `forward_auth`
✅ [**Prometheus-Stack**] - Optional monitoring with Prometheus, node-exporter, cAdvisor and Pushgateway; Grafana datasource automatically provisioned; PLC exporter for MQTT + Modbus + OPC-UA
✅ **[Teams-Bot + Asana]** - n8n workflows: Azure Bot Service → Ollama LLM responses in Teams; Grafana alerts as Adaptive Cards; daily Asana task report
✅ [**osTicket AI Integration**] - n8n reads directly from osTicket MySQL DB, generates solution suggestions via Ollama + Qdrant similarity search and posts internal notes; resolved tickets automatically flow into Neo4j + Qdrant
✅ **[Knowledge Base (KB)]** – Two ingest workflows: PDF/Documents or web research via webhook → Embedding + NER → Qdrant (`knowledge_base`) + Neo4j parallel indexed
✅ [**Langfuse**](https://langfuse.com/) - Open source LLM engineering platform for agent observability

---

## 🌟 Features

- ✅ Local or server hosted Ollama and/or public LLMs
- ✅ Hermes Agent: autonomous AI agent with Teams gateway, web dashboard, autostart with the stack, controllable via dashboard macro
- ✅ JWT Auth via Caddy `forward_auth` – all services protected
- ✅ TOTP/2FA via Supabase GoTrue (no extra container)
- ✅ Supabase with Vector Store & Authentication
- ✅ Crawl4AI, Qdrant, Neo4j, Langfuse, Python NLP/Document Service (OCR + NER, DE+EN), MinIO, Open WebUI, ...
- ✅ TTS Service: Voice Cloning (OmniVoice, 600+ languages), Video Dubbing (Whisper + Ollama + ffmpeg), Apple Silicon MPS
- ✅ Grafana Monitoring with Caddy Routing + Auth Proxy Header
- ✅ On-Demand Service Control: Dashboard Admin Tab, REST API, n8n Toolcall
- ✅ Ollama defaults to native on host – no Ollama container during normal start
- ✅ Prometheus Monitoring: node-exporter, cAdvisor, Pushgateway, PLC exporter (MQTT/Modbus/OPC-UA)
- ✅ Teams-Bot + Asana: n8n workflows for chat, Grafana alerts, task reports
- ✅ osTicket AI: direct MySQL access, solution suggestions via Qdrant + Ollama, auto KB sync
- ✅ Knowledge Base: PDF/web research → Qdrant + Neo4j; tickets automatically flow in
- ✅ Superadmin/Admin/User role hierarchy with rate-limiting on all control endpoints
- ✅ Automated startup & cleanup via `start_services.py`

---

Before you begin, make sure you have the following software installed:

- [Python](https://www.python.org/downloads/) - Required to run the setup script
- [Git/GitHub Desktop](https://desktop.github.com/) - For easy repository management
- [Docker/Docker Desktop](https://www.docker.com/products/docker-desktop/) - Required to run all services

---

## 🔧 Quickstart

```bash
git clone -b stable https://github.com/nic0711/local-ai-masterbrain
cd local-ai-masterbrain
cp .env.example .env              # Enter secrets!
python3 start_services.py         # Default: Ollama runs natively on host
# python3 start_services.py --profile gpu-nvidia     # Nvidia GPU (without Ollama container)
# docker compose --profile ollama-docker up -d       # Ollama as Docker container
```

> More details about `--profile` and `--environment`: [docs/03_start_services.md](docs/03_start_services.md)

👉 Dashboard: https://brain.local  
👉 n8n: https://n8n.brain.local  
👉 Open WebUI: https://webui.brain.local  

---

## 📚 Documentation

| Topic                    | File                                    |
|--------------------------|------------------------------------------|
| Installation             | [01_installation.md](docs/01_installation.md) |
| Configuration (.env)     | [02_configuration.md](docs/02_configuration.md) |
| Start script (details)   | [03_start_services.md](docs/03_start_services.md) |
| Cloud deployment         | [04_cloud_deployment.md](docs/04_cloud_deployment.md) |
| Security hardening       | [05_security_hardening.md](docs/05_security_hardening.md) |
| Usage: n8n & WebUI       | [06_usage_n8n_openwebui.md](docs/06_usage_n8n_openwebui.md) |
| Troubleshooting          | [07_troubleshooting.md](docs/07_troubleshooting.md) |
| Backup & recovery        | [08_backup_and_recovery.md](docs/08_backup_and_recovery.md) |
| FAQ & tips               | [09_faq.md](docs/09_faq.md) |
| Python NLP/Document Service | [10_python_nlp_service.md](docs/10_python_nlp_service.md) |
| Obsidian Integration     | [11_obsidian_integration.md](docs/11_obsidian_integration.md) |
| Monitoring (Uptime Kuma) | [12_monitoring.md](docs/12_monitoring.md) |
| GraphRAG (Neo4j Knowledge Graph) | [13_graphrag.md](docs/13_graphrag.md) |
| Links & resources        | [tips_links.md](docs/tips_links.md) |
| OCR Service              | [14_ocr_service.md](docs/14_ocr_service.md) |
| API Reference            | [15_api_reference.md](docs/15_api_reference.md) |
| Scraping Configurator    | [16_scraping_configurator.md](docs/16_scraping_configurator.md) |
| Dashboard Architecture   | [17_dashboard_changes.md](docs/17_dashboard_changes.md) |
| TTS / Voice Cloning / Dubbing | [18_tts_service.md](docs/18_tts_service.md) |
| On-Demand Services (Service Control) | [19_on_demand_services.md](docs/19_on_demand_services.md) |
| Resource Optimization (Memory, Logging) | [20_resource_optimization.md](docs/20_resource_optimization.md) |
| Hermes Agent (AI Agent, Teams, Web-UI) | [21_hermes_agent.md](docs/21_hermes_agent.md) |
| Monitoring (Prometheus, cAdvisor, Pushgateway) | [23_monitoring.md](docs/23_monitoring.md) |
| PLC Monitoring (OPC-UA, MQTT, Modbus) | [24_sps_monitoring.md](docs/24_sps_monitoring.md) |
| Teams Bot + Asana Integration | [25_teams_bot.md](docs/25_teams_bot.md) |
| osTicket AI Integration  | [26_osticket_ki.md](docs/26_osticket_ki.md) |
| Knowledge Base (KB Workflows) | [27_knowledge_base.md](docs/27_knowledge_base.md) |

---

## 📋 Changelog

### 2026-07 – Focus on Hermes Agent: Odysseus Removed, Dashboard Cleanup

| What | Details |
|-----|---------|
| **Odysseus removed** | AI workspace fully removed (Git submodule, Compose services, Caddy route, dashboard card, `docs/22_odysseus_workspace.md`) – focus is now clearly on Hermes Agent |
| **Hermes upgraded** | Own logo instead of generic Python icon, more prominent dashboard position, `HERMES_HOSTNAME` env bug fixed in the `dashboard` service |
| **Hermes dashboard bugfix** | Container refused to bind to `0.0.0.0` without an auth provider → `HERMES_DASHBOARD_USER/PASSWORD/AUTH_SECRET` added as required fields (see note above) |
| **Central service catalog** | `dashboard/services.js` replaces three diverged service lists (`health.js`/`admin.js`/`control.js`) – fixes Hermes missing from the admin system status |
| **Admin tab restructured** | 4 logical sections: System Status & Control, Backup, Logs & Diagnostics, User Management |
| **Supabase submodule fixed** | Missing `.gitmodules` entry added, `.git/modules/supabase` initialized via `git submodule absorbgitdirs`, gitlink pointer updated |

### 2026-07 – Team Server: Hermes Agent, Monitoring, Teams, osTicket, Knowledge Base

| What | Details |
|-----|---------|
| **Role Hierarchy** | Superadmin / Admin / User via `SUPERADMIN_EMAILS` / `ADMIN_EMAILS`; Rate-limiting on all control endpoints |
| **Hermes Agent** | `agent.brain.local` – autonomous AI agent (NousResearch, MIT) with web dashboard + Microsoft Teams gateway; Git submodule, builds locally; runs on local Ollama; `AUTOSTART_HERMES=true` by default |
| **Prometheus Monitoring** | Profile `monitoring`: Prometheus, node-exporter, cAdvisor, Pushgateway; Grafana datasource auto-provisioned; Dashboard macros for start/stop |
| **PLC Monitoring** | mqtt2prometheus + modbus-exporter (profile `monitoring`); OPC-UA as Grafana plugin; configuration templates in `sps-monitoring/` |
| **Teams Bot** | n8n workflow: Azure Bot Service → Ollama LLM; SSRF protection, JWT format check, prompt injection mitigation |
| **Grafana → Teams Alerts** | n8n workflow: Grafana Unified Alerting → Teams Adaptive Cards via Incoming Webhook |
| **Asana Sync** | n8n workflow: overdue + soon-due tasks as Teams message daily |
| **osTicket AI** | Direct MySQL access: solution suggestions via Qdrant + Ollama, internal note in ticket; resolved tickets → KB |
| **KB Workflows** | PDF/document ingest + web research webhook → embedding → Qdrant `knowledge_base` + Neo4j (parallel) |
| **New Docs** | 21, 23–27: Hermes Agent, Monitoring, PLC, Teams, osTicket, Knowledge Base |

### 2026-07 – Ollama: Host-First as Default

| What | Details |
|-----|---------|
| `docker-compose.yml` | Ollama container (`ollama-cpu/gpu/gpu-amd` + init services) removed from profiles `cpu`/`gpu-nvidia`/`gpu-amd` – new separate profile `ollama-docker` |
| `n8n` | `OLLAMA_HOST`: `ollama:11434` → `http://host.docker.internal:11434` |
| `tts-service` | `OLLAMA_HOST`: `http://ollama:11434` → `http://host.docker.internal:11434` |
| Default Behavior | `python3 start_services.py` starts **no** Ollama container anymore; Ollama runs natively on host |
| Ollama as Container | Only with explicit `docker compose --profile ollama-docker up -d` |

### 2026-07 – Hermes Agent

| What | Details |
|-----|---------|
| `hermes-agent/` | Git submodule (NousResearch/hermes-agent, MIT) |
| `hermes-gateway` | Autonomous AI agent process with Microsoft Teams gateway |
| `hermes-dashboard` | Web UI at `agent.brain.local` behind Caddy `forward_auth` |
| `hermes-config/cli-config.yaml` | Local Ollama configured as LLM provider (`qwen2.5:7b`) |
| `dashboard/macros.json` | Macros "Start Hermes Agent" + "Stop" |
| `auth-gateway/app.py` | `hermes-gateway` + `hermes-dashboard` registered in service control |
| `docs/21_hermes_agent.md` | Setup, Teams registration, model configuration |

### 2026-07 – Security Hardening: Admin Roles, JWT Audience, CSP

| What | Details |
|-----|---------|
| `auth-gateway/app.py` | Admin role control: `ADMIN_EMAILS` env var + `_require_admin()`; 11 privileged `/control/*` endpoints require admin rights |
| `auth-gateway/app.py` | JWT audience verification: `aud: "authenticated"` is checked (prevents misuse of service-role tokens) |
| `Caddyfile` | Grafana admin email from hardcoded `wolf@datista.de` → `{$GRAFANA_ADMIN_EMAIL}` (env var) |
| `.env.example` | `GRAFANA_ADMIN_EMAIL` and `ADMIN_EMAILS` documented |
| `Caddyfile` | Content Security Policy for dashboard block (script-src CDN whitelist, connect-src Supabase, frame-ancestors none) |
| `n8n-tool-workflows/stack-service-control.json` | Confused Deputy Fix: caller JWT forwarded instead of privileged workflow credential; `X-Webhook-Token` as webhook auth |
| `docs/05_security_hardening.md` | Admin roles, JWT audience, CSP, cookie properties and known limitations documented |
| `docs/15_api_reference.md` | Auth level (auth vs. admin) per endpoint added |

### 2026-06 – Grafana, n8n On-Demand Service Control

| What | Details |
|-----|---------|
| `grafana` | Grafana integrated in stack (`grafana.{DOMAIN}`), with Caddy routing and auth proxy header |
| `n8n-tool-workflows/stack-service-control.json` | n8n workflow to start/stop stack services via AI agent toolcall |
| `dashboard/macros.json` | Macros extended (light-mode, research, rag-mode, langfuse-start, save-resources, restart-core) |
| `docs/19_on_demand_services.md` | New docs: Service Control (Dashboard, REST API, n8n Toolcall, Macros) |
| `docs/20_resource_optimization.md` | New docs: Memory limits, logging, disk maintenance, custom image updates |

---

### 2026-04 – Fix: Docker Compose Project Name

| What | Details |
|-----|---------|
| `docker-compose.yml` | `name: localai` set – project name now fixed, no `-p localai` needed anymore |

---

### 2026-04 – TTS Service: Voice Cloning & Video Dubbing

| What | Details |
|-----|---------|
| `tts-service/` | New FastAPI container (port 8003) with [OmniVoice](https://github.com/k2-fsa/OmniVoice) – 600+ languages, RTF 0.025 (40x real-time), Apple Silicon MPS |
| Voice Cloning | Zero-shot from 5–15s reference audio; `ref_text` optional (internal Whisper ASR) |
| Voice Design | Voice via attribute description (`"female, british accent"`) without reference audio |
| Video Dubbing | Async pipeline: ffmpeg → Whisper → Ollama → OmniVoice → ffmpeg; YouTube URL support |
| `caddy-addon/tts.conf` | Caddy route `tts.{DOMAIN}` with `forward_auth` + 600s timeout for dubbing |
| `docker-compose.yml` | `tts-service` block + `TTS_HOSTNAME` in both Caddy instances |
| `docs/18_tts_service.md` | Full docs: setup, all 7 endpoints, pipeline, device config, volumes |
| `docs/15_api_reference.md` | TTS service added to API overview |

### 2026-03 – OCR Service, Scraping Configurator & API Reference

| What | Details |
|-----|---------|
| `ocr-service/` | New FastAPI container with TrOCR + Tesseract, 15 endpoints, auto engine selection |
| `caddy-addon/ocr.conf` | Caddy route for `ocr.{DOMAIN}` with forward_auth |
| `ocr_storage/` | Input/output/temp directories for OCR processing |
| `supabase/…/02-04_*.sql` | SQL schema for `scraped_content` table |
| `n8n-tool-workflows/scraping-configurator.json` | Configurable scraper: mode (css/llm/auto) × destination (supabase/neo4j/qdrant/sheets/webhook/all) |
| `n8n-tool-workflows/api-health-reference.json` | Live API reference workflow with health checks + endpoint catalog |
| `n8n-tool-workflows/ocr-processing-workflow.json` | N8N workflow for OCR batch processing |
| `docs/14_ocr_service.md` | OCR service docs: setup, all 15 endpoints, models, storage |
| `docs/15_api_reference.md` | Full API reference: 43 endpoints across 3 services |
| `docs/16_scraping_configurator.md` | Scraping configurator guide: modes, destinations, examples |
| `docs/17_dashboard_changes.md` | Dashboard architecture: auth flow, tabs, cards, JS bridges, Whisper |

### 2026-03 – Auth System: Caddy forward_auth + TOTP/2FA

**Full JWT-based authentication for all services**

| Component | What |
|---|-----|
| `auth-gateway/app.py` | Cookie fallback: reads `sb-access-token` from cookie if no Authorization header present |
| `dashboard/auth.js` | Cookie management: sets JWT after login as `sb-access-token` cookie on `.brain.local`; `onAuthStateChange` keeps cookie current during token refresh |
| `dashboard/auth.js` | TOTP/2FA flow: automatic MFA check after password login, TOTP challenge step |
| `dashboard/auth.js` | 2FA enrollment: QR code display via Supabase `mfa.enroll()`, confirmation with 6-digit code |
| `dashboard/login.html` | Two-step login form (password → TOTP), initial TOTP step hidden |
| `dashboard/index.html` | "Set up 2FA" button + modal with QR code and enrollment flow |
| `Caddyfile` | `(protected)` snippet: `forward_auth auth-gateway:5001` with cookie forwarding as Bearer header; dashboard without `forward_auth` (prevents redirect loop) |
| `Caddyfile` | SearXNG, Qdrant (`qdrant:6333`), Minio (`minio:9001`) as new protected vHosts |
| `Caddyfile` | Crawl4AI port corrected: `8082` → `11235` |
| `docker-compose.yml` | auth-gateway: profile `public` → `auth` (activated via `--profile auth`) |
| `start_services.py` | `--environment public` is new default; `--profile auth` + `public.supabase.yml` automatically with `--environment public` |
| `docker-compose.override.public.supabase.yml` | GoTrue TOTP enabled: `GOTRUE_MFA_ENABLED=true`, `GOTRUE_MFA_TOTP_ENABLED=true` |
| `.env.example` | `QDRANT_HOSTNAME`, `MINIO_HOSTNAME` added; production example on `yourdomain.com` |

### 2026-03 – Python NLP/Document Service v2.0

**`python-nlp-service/` – OCR + multilingual NER**

| Component | Old | New |
|-----------|-----|-------|
| Functionality | German-only NER | NER (DE+EN) + OCR + PDF extraction |
| SpaCy models | `de_core_news_md` | `de_core_news_md` + `en_core_web_md` |
| OCR | — | Via Ollama `glm-ocr` (configurable via `OCR_MODEL`) |
| PDF Extraction | — | PyMuPDF (direct + OCR fallback for scanned PDFs) |
| New Main Endpoint | — | `POST /document/analyze` (text + entities in one call) |
| Compat Endpoints | — | `/pdf/extract`, `/pdf/analyze-type`, `/pdf/to-png-smart` |
| RAM Limit | 1 GB | 1.5 GB (two SpaCy models) |
| New Env Vars | — | `OLLAMA_HOST`, `OCR_MODEL` |
| extra_hosts | — | `host.docker.internal:host-gateway` (Linux compatibility) |
| n8n depends_on | commented out | active (`service_healthy`) |

---

### 2026-02 – Dependency Updates

**Python packages updated to latest (CVE-clean, verified via OSV.dev)**

| Package | Old | New | Files |
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

**Supabase Submodule Pointer Updated**

| Component | Old | New |
|-----------|-----|-------|
| Pointer | `169e3d9` | `571e060` |
| supabase-studio | 2025.11.10 | **2026.02.16** |
| gotrue (auth) | v2.182.1 | **v2.186.0** |
| postgrest | v13.0.7 | **v14.5** ⚠️ Major |
| realtime | v2.63.0 | **v2.76.5** |

---

### 2026-02 – Docker Compose & Infrastructure

**`docker-compose.yml` – Bug fixes & improvements**

| Priority | Service | What | Fix |
|------|---------|-----|-----|
| 🔴 Bug | `python-nlp-service` | Healthcheck tested port `5050` instead of `5000` – container permanently marked as `unhealthy` | Port corrected |
| 🟠 Stability | `open-webui` | Image tag `:main` (development branch, unstable) | → `:latest` |
| 🟠 Correctness | `python-nlp-service` | `FLASK_ENV=production` deprecated since Flask 2.2, ineffective with Gunicorn operation | Variable removed |
| 🟠 Ops | `python-nlp-service`, `neo4j` | `restart: always` restarts container even after manual `docker stop` | → `unless-stopped` |
| 🟠 Ops | `n8n`, `python-nlp-service`, `open-webui`, `neo4j` | No log rotation configured, logs can grow uncontrolled | `json-file` driver with `max-size: 10m / max-file: 3` |
| 🟡 Usability | `neo4j` | No `container_name`, no healthcheck | `container_name: neo4j` + HTTP check on port 7474 |

**`start_services.py` – Bug fix**

| Priority | Functionality | What | Fix |
|------|----------|-----|-----|
| 🔴 Bug | `check_and_fix_docker_compose_for_searxng()` | SearXNG `cap_drop`-fix searched for `"cap_drop: - ALL"` as single line, YAML contains multi-line format (`cap_drop:\n  - ALL`) → condition always false, SearXNG could fail on first start | Search string changed to correct multi-line format, uniquely followed by subsequent `cap_add: CHOWN` |

---

### 2026-02 – Python NLP Service

**`python-nlp-service/` – Version update & optimization**

| Component | Before | After | Note |
|-----------|--------|-------|---------|
| Python | 3.11 | **3.12** | |
| SpaCy model | `de_core_news_sm` (~13 MB) | **`de_core_news_md`** (~43 MB) | Better NER quality, no GPU needed |
| NumPy | 1.26.x | **2.2.x** | Breaking changes to 1.x; SpaCy 3.8.x and pandas 2.2.x compatible |
| Flask | 3.0.0 | **3.1.0** | |
| Gunicorn | 21.2.0 | **23.0.0** | |
| spaCy | 3.7.5 | **3.8.3** | |
| pandas | 2.1.4 | **2.2.3** | |
| requests | 2.31.0 | **2.32.3** | |
| python-json-logger | 2.0.7 | **3.0.0** | |
| Dockerfile structure | Site-packages copied directly | **Virtual Environment** `/opt/venv` | Clean isolation, no accidental copying of build tools |
| Security | Root user, no fixed UID | **Non-root UID 1001** | |
| Monitoring | No docker HEALTHCHECK | **`HEALTHCHECK`** via `/health` endpoint | |
| OCR | — | Via **Ollama** (not in this container) | |

---

### 2026-02 – Security Hardening & Improvements

**`auth-gateway/` – Full security hardening**

| Priority | Component | What | Fix |
|------|-----------|-----|-----|
| 🔴 Security | `Dockerfile` | Root user, no multi-stage build, no fixed UID, no HEALTHCHECK, no apt-get upgrade | Multi-stage build + virtual environment `/opt/venv`, non-root UID 1002, HEALTHCHECK, apt-get upgrade |
| 🔴 Security | `app.py` | Sensitive token data written to logs → potential credential exposure | Sensitive data fully removed; generic warning message |
| 🟠 Stability | `app.py` | No `/health` endpoint → HEALTHCHECK and monitoring impossible | `/health`-endpoint added |
| 🟠 Versions | `requirements.txt` | `flask==3.0.0`, `gunicorn==21.2.0`, `supabase==2.4.2` (>1 year old) | `flask==3.1.0`, `gunicorn==23.0.0`, `supabase==2.28.0` |

**`python-nlp-service/app.py` – DoS Protection**

| Priority | Component | What | Fix |
|------|-----------|-----|-----|
| 🔴 Security | `/process` endpoint | No input size limit → arbitrarily large texts possible (DoS) | Max input size limited; HTTP 413 on exceedance |

**`Caddyfile` – Security Headers**

| Priority | Component | What | Fix |
|------|-----------|-----|-----|
| 🟠 Security | All vHosts | No security headers configured | `(security_headers)` snippet with HSTS, X-Content-Type Options, X Frame Options, Referrer Policy, Permissions Policy, `-Server` in all active vHosts |

**`backup.sh` – .env Backup**

| Priority | Component | What | Fix |
|------|-----------|-----|-----|
| 🟠 Ops | `.env` | Configuration file with secrets not backed up | `.env` copied to backup directory with `chmod 600` |

**`docker-compose.yml` – crawl4ai Resource Limits**

| Priority | Component | What | Fix |
|------|-----------|-----|-----|
| 🟠 Stability | `crawl4ai` | No resource limits, no healthcheck | Memory limit 3 GB (reservation 512 MB), HEALTHCHECK on `/health` port 11235 |

**`dashboard/index.html` – CDN Subresource Integrity**

| Priority | Component | What | Fix |
|------|-----------|-----|-----|
| 🟡 Supply Chain | `supabase-js` CDN | Floating tag `@2` without SRI hash → CDN compromise possible | Pinned version `@2.97.0` + `integrity="sha384-..."` + `crossorigin="anonymous"` |

**CVE Scan (`pip-audit` + OSV.dev) – Version Correction**

| CVE/GHSA | Package | Affected | Fix | Description |
|----------|-------|-----------|-----|--------------|
| CVE-2025-47278 | `flask` | 3.1.0 | **3.1.1** | Signing key order inverted → wrong key used for signing |
| GHSA-9hjg-9r4m-mvj7 | `requests` | 2.32.3 | **2.32.4** | `.netrc` credentials leak via manipulated URLs |
| GHSA-hgf8-39gv-g3f2 | `werkzeug` | 3.1.3 | **3.1.5** | `safe_join()` allows Windows special device names |
| GHSA-87hc-h4r5-73f7 | `werkzeug` | 3.1.3 | **3.1.5** | `safe_join()` allows special device names with compound suffixes |

Fixes applied in `auth-gateway/requirements.txt` and `python-nlp-service/requirements.txt`.

---

📜 License: Apache 2.0 – see [LICENSE](LICENSE)

---

### 2026-03 – Upstream Sync (coleam00/local-ai-packaged)

Selective adoption of 13 upstream commits. Our additions (auth-gateway, dashboard, docs, python-nlp-service) remain fully intact.

| What | Upstream Commit | Adoption |
|---|---|---------|
| `n8n-import` service removed | `48c186a`, `8d02114` | ✅ Service + `depends_on` entry removed |
| n8n `LocalFileTrigger` + `ExecuteCommand` activatable | `ce882b7` | ✅ `NODES_EXCLUDE` comment added in x-n8n |
| New Supabase Storage Env Vars | `57c194a` | ✅ Added to `.env.example` |
| New n8n workflow files (V1/V2/V3 RAG Agent) | `5c55af2` | ✅ Copied into `n8n/backup/workflows/` |
| Shared volume path: `:/home/node/.n8n-files/shared` → `:/data/shared` | `8d02114` | ✅ Adopted |
| `LANGFUSE_ENCRYPTION_KEY` → `ENCRYPTION_KEY` | — | ✅ In `docker-compose.yml` + `.env.example` |
| Caddy hostnames without `${DOMAIN}` | — | ⏭️ Not adopted (our setup uses `${DOMAIN}`) |
| `open-webui:latest` → `:main` | — | ⏭️ Not adopted (`:latest` more stable) |
| `crawl4ai` removed | — | ⏭️ Not adopted (part of our stack) |
| `neo4j` restart: always, no healthcheck | — | ⏭️ Not adopted (we keep our healthcheck) |
