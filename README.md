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

- ✅ [**Selbst gehostetes n8n**](https://n8n.io/) – Low-code-Plattform mit über 400 Integrationen und fortschrittlichen AI-Komponenten; Code-Nodes laufen isoliert im Sidecar `n8n-runners` (externe Task-Runner)
- ✅ **[Dashboard mit Auth]** – Übersichtsseite aller Services mit JWT-basierter Authentifizierung (E-Mail + Passwort + TOTP/2FA, standardmäßig verpflichtend), geschützt durch Caddy `forward_auth`
- ✅ [**Supabase**](https://supabase.com/) – Open-Source-Datenbank als Service – am weitesten verbreitete Datenbank für KI-Agenten
- ✅ [**Ollama**](https://ollama.com/) – Cross-platform LLM-Plattform zum Installieren und Ausführen der neuesten lokalen LLMs
- ✅ [**Open WebUI**](https://openwebui.com/) – ChatGPT-artige Schnittstelle zur privaten Interaktion mit Ihren lokalen Modellen und N8N-Agenten
- ✅ [**Hermes Agent**](https://github.com/NousResearch/hermes-agent) – Autonomer KI-Agent (NousResearch, MIT) mit Web-Dashboard und Microsoft Teams Gateway; läuft auf lokalem Ollama, startet standardmäßig automatisch mit dem Stack
- ✅ [**Crawl4ai**](https://crawl4ai.com/) - Scraping / Crawling für LLM-Nutzung oder Datenaggregation, Screenshots usw.
- ✅ [**TTS Service / Voice Cloning / Video Dubbing**] – Lokaler Text-zu-Sprache-Container mit [OmniVoice](https://github.com/k2-fsa/OmniVoice) (600+ Sprachen, RTF 0.025). Zero-Shot Voice Cloning aus 5–15s Referenz-Audio, Voice Design via Attributbeschreibung (Geschlecht, Akzent, Tonlage), asynchrones Video-Dubbing mit Whisper-Transkription und Ollama-Übersetzung.
- ✅ [**Python NLP / Document Service**] – Produktionsreifer Dokumentenverarbeitungscontainer mit Flask/Gunicorn. Extrahiert Text aus PDFs und Bildern, führt OCR via **Ollama glm-ocr** durch (kein lokaler Tesseract erforderlich) und führt Named Entity Recognition (NER) auf Deutsch und Englisch via SpaCy durch. Bietet eine einzelne `/document/analyze`-Endpunkt, der Text + Entitäten in einem Aufruf zurückgibt – ideal als Vorverarbeitungspipeline für Neo4j Knowledge Graphs und n8n-Arbeitsabläufe.
- ✅ [**Qdrant**](https://qdrant.tech/) - Open Source, High Performance Vector Store mit einer umfassenden API. Obwohl Sie Supabase für RAG verwenden können, wurde dies beibehalten (im Gegensatz zu Postgres), da es schneller als Supabase ist und manchmal die bessere Option darstellt.
- ✅ [**Neo4j**](https://neo4j.com/) - Knowledge Graph Engine, die Tools wie GraphRAG, LightRAG und Graphiti antreibt
- ✅ [**SearXNG**](https://searxng.org/) - Open Source, kostenloser Internet-Metasuchmotor, der Ergebnisse von bis zu 229 Suchdiensten aggregiert. Benutzer werden weder verfolgt noch profiliert, daher die Passform zum lokalen KI-Paket.
- ✅ [**Caddy**](https://caddyserver.com/) – Managed HTTPS/TLS für benutzerdefinierte Domains
- ✅ [**Grafana**](https://grafana.com/) - Monitoring & Dashboards für Stack-Metriken, Container-Health und Logs
- ✅ [**Uptime Kuma**](https://github.com/louislam/uptime-kuma) – Self-hosted Uptime-Monitoring mit Status-Page (`status.brain.local`), Benachrichtigungen und Maintenance-Windows; eine der wenigen Ausnahmen ohne Caddy `forward_auth`
- ✅ [**Prometheus-Stack**] – Optionales Monitoring mit Prometheus, node-exporter, cAdvisor, Pushgateway und Blackbox-Exporter; Grafana-Datasource automatisch bereitgestellt; SPS-Anbindung für MQTT + OPC-UA
- ✅ **[Teams-Bot + Asana]** - n8n-Arbeitsabläufe: Azure Bot Service → Ollama LLM-Antworten in Teams; Grafana-Alerts als Adaptive Cards; täglicher Asana-Task-Bericht
- ✅ [**osTicket KI-Integration**] – n8n liest direkt aus der osTicket-MySQL-Datenbank, generiert Lösungsvorschläge via Ollama + Qdrant-Ähnlichkeitssuche und postet interne Notizen; gelöste Tickets fließen automatisch in Neo4j + Qdrant
- ✅ [**Wissensdatenbank (KB)**] – Zwei Ingest-Arbeitsabläufe: PDF/Dokumente oder Web-Research per Webhook → Embedding + NER → Qdrant (`knowledge_base`) + Neo4j parallel indiziert

---

## 🌟 Features

- ✅ Lokaler oder servergehosteter Ollama und/oder öffentliche LLMs
- ✅ Hermes Agent: autonomer KI-Agent mit Teams-Gateway, Web-Dashboard, Autostart mit dem Stack, steuerbar per Dashboard-Macro
- ✅ JWT-Authentifizierung via Caddy `forward_auth` – alle Services geschützt
- ✅ TOTP/2FA über Supabase GoTrue (kein extra Container), serverseitig via `aal2`-Check im auth-gateway erzwungen
- ✅ Supabase mit Vector Store & Authentifizierung
- ✅ Crawl4AI, Qdrant, Neo4j, Python NLP/Dokumentenservice (OCR + NER, DE+EN), Open WebUI, ...
- ✅ TTS Service: Voice Cloning (OmniVoice, 600+ Sprachen), Video-Dubbing (Whisper + Ollama + ffmpeg), Apple Silicon MPS
- ✅ Grafana Monitoring mit Caddy-Routing + Auth-Proxy-Header
- ✅ On-Demand Service Control: Dashboard Admin-Tab, REST API, n8n Toolcall
- ✅ Ollama standardmäßig nativ auf dem Host – kein Ollama Container beim normalen Start
- ✅ Prometheus Monitoring: node-exporter, cAdvisor, Pushgateway, Blackbox, SPS-Anbindung (MQTT/OPC-UA)
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
git clone --recurse-submodules https://github.com/nic0711/local-ai-masterbrain
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
| Verfügbarkeits-Monitoring (Uptime Kuma) | [12_monitoring.md](docs/12_monitoring.md) |
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
| Metrik-Monitoring (Prometheus, cAdvisor, Pushgateway, Blackbox) | [23_monitoring.md](docs/23_monitoring.md) |
| SPS-Monitoring (OPC-UA, MQTT) | [24_sps_monitoring.md](docs/24_sps_monitoring.md) |
| Teams Bot + Asana-Integration | [25_teams_bot.md](docs/25_teams_bot.md) |
| osTicket KI Integration  | [26_osticket_ki.md](docs/26_osticket_ki.md) |
| Wissensdatenbank (KB-Arbeitsabläufe) | [27_knowledge_base.md](docs/27_knowledge_base.md) |
| Intune Geräte-Inventar (Grafana-Dashboard) | [28_intune_inventory.md](docs/28_intune_inventory.md) |
| Supabase-Migrationen (projekteigenes Schema) | [29_supabase_migrations.md](docs/29_supabase_migrations.md) |
| Zielarchitektur (Governance-Baseline) | [CONTEXT.md](CONTEXT.md) |
| Architektur-Entscheidungen (ADRs)     | [docs/adr/](docs/adr/) |
| Umsetzungsplan & Governance-Planung   | [docs/planning/](docs/planning/) |
| Betriebshandbuch (im Aufbau)          | [docs/handbook/](docs/handbook/) |

---

## 📋 Changelog

Vollständige Änderungshistorie: [CHANGELOG.md](CHANGELOG.md)

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

- ✅ [**Self-hosted n8n**](https://n8n.io/) - Low-code platform with over 400 integrations and advanced AI components; Code nodes run isolated in the `n8n-runners` sidecar (external task runners)
- ✅ **[Dashboard with Auth]** – Overview page of all services with JWT-based authentication (Email + Password + TOTP/2FA, enforced by default), protected by Caddy `forward_auth`
- ✅ [**Supabase**](https://supabase.com/) - Open source database as a service - most widely used database for AI agents
- ✅ [**Ollama**](https://ollama.com/) - Cross-platform LLM platform to install and run the latest local LLMs
- ✅ [**Open WebUI**](https://openwebui.com/) - ChatGPT-like interface to privately interact with your local models and N8N agents
- ✅ [**Hermes Agent**](https://github.com/NousResearch/hermes-agent) - Autonomous AI agent (NousResearch, MIT) with web dashboard and Microsoft Teams gateway; runs on local Ollama, starts automatically with the stack by default
- ✅ [**Crawl4ai**](https://crawl4ai.com/) - scraping / crawling for LLM usage or data aggregation, screenshots, etc.
- ✅ [**TTS Service / Voice Cloning / Video Dubbing**] - Local Text-to-Speech container with [OmniVoice](https://github.com/k2-fsa/OmniVoice) (600+ languages, RTF 0.025). Zero-Shot Voice Cloning from 5–15s reference audio, voice design via attribute description (gender, accent, tone), asynchronous video dubbing with Whisper transcription and Ollama translation.
- ✅ [**Python NLP / Document Service**] - Production-ready document processing container with Flask/Gunicorn. Extracts text from PDFs and images, runs OCR via **Ollama glm-ocr** (no local Tesseract needed), and performs Named Entity Recognition (NER) in German and English via SpaCy. Provides a single `/document/analyze` endpoint that returns text + entities in one call – ideal as preprocessing pipeline for Neo4j Knowledge Graphs and n8n workflows.
- ✅ [**Qdrant**](https://qdrant.tech/) - Open source, high performance vector store with comprehensive API. Even though you can use Supabase for RAG, this was kept unlike Postgres since it's faster than Supabase so sometimes is the better option.
- ✅ [**Neo4j**](https://neo4j.com/) - Knowledge graph engine that powers tools like GraphRAG, LightRAG, and Graphiti
- ✅ [**SearXNG**](https://searxng.org/) - Open source, free internet metasearch engine which aggregates results from up to 229 search services. Users are neither tracked nor profiled, hence the fit with the local AI package.
- ✅ [**Caddy**](https://caddyserver.com/) - Managed HTTPS/TLS for custom domains
- ✅ [**Grafana**](https://grafana.com/) - Monitoring & Dashboards for stack metrics, container health and logs
- ✅ [**Uptime Kuma**](https://github.com/louislam/uptime-kuma) - Self-hosted uptime monitoring with status page (`status.brain.local`), notifications and maintenance windows; one of the few exceptions without Caddy `forward_auth`
- ✅ [**Prometheus-Stack**] - Optional monitoring with Prometheus, node-exporter, cAdvisor, Pushgateway and Blackbox exporter; Grafana datasource automatically provisioned; PLC integration for MQTT + OPC-UA
- ✅ **[Teams-Bot + Asana]** - n8n workflows: Azure Bot Service → Ollama LLM responses in Teams; Grafana alerts as Adaptive Cards; daily Asana task report
- ✅ [**osTicket AI Integration**] - n8n reads directly from osTicket MySQL DB, generates solution suggestions via Ollama + Qdrant similarity search and posts internal notes; resolved tickets automatically flow into Neo4j + Qdrant
- ✅ **[Knowledge Base (KB)]** – Two ingest workflows: PDF/Documents or web research via webhook → Embedding + NER → Qdrant (`knowledge_base`) + Neo4j parallel indexed

---

## 🌟 Features

- ✅ Local or server hosted Ollama and/or public LLMs
- ✅ Hermes Agent: autonomous AI agent with Teams gateway, web dashboard, autostart with the stack, controllable via dashboard macro
- ✅ JWT Auth via Caddy `forward_auth` – all services protected
- ✅ TOTP/2FA via Supabase GoTrue (no extra container), enforced server-side via `aal2` check in the auth-gateway
- ✅ Supabase with Vector Store & Authentication
- ✅ Crawl4AI, Qdrant, Neo4j, Python NLP/Document Service (OCR + NER, DE+EN), Open WebUI, ...
- ✅ TTS Service: Voice Cloning (OmniVoice, 600+ languages), Video Dubbing (Whisper + Ollama + ffmpeg), Apple Silicon MPS
- ✅ Grafana Monitoring with Caddy Routing + Auth Proxy Header
- ✅ On-Demand Service Control: Dashboard Admin Tab, REST API, n8n Toolcall
- ✅ Ollama defaults to native on host – no Ollama container during normal start
- ✅ Prometheus Monitoring: node-exporter, cAdvisor, Pushgateway, Blackbox, PLC integration (MQTT/OPC-UA)
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
git clone --recurse-submodules https://github.com/nic0711/local-ai-masterbrain
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
| Uptime monitoring (Uptime Kuma) | [12_monitoring.md](docs/12_monitoring.md) |
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
| Metrics monitoring (Prometheus, cAdvisor, Pushgateway, Blackbox) | [23_monitoring.md](docs/23_monitoring.md) |
| PLC Monitoring (OPC-UA, MQTT) | [24_sps_monitoring.md](docs/24_sps_monitoring.md) |
| Teams Bot + Asana Integration | [25_teams_bot.md](docs/25_teams_bot.md) |
| osTicket AI Integration  | [26_osticket_ki.md](docs/26_osticket_ki.md) |
| Knowledge Base (KB Workflows) | [27_knowledge_base.md](docs/27_knowledge_base.md) |
| Intune Device Inventory (Grafana Dashboard) | [28_intune_inventory.md](docs/28_intune_inventory.md) |
| Supabase migrations (project-owned schema) | [29_supabase_migrations.md](docs/29_supabase_migrations.md) |
| Target architecture (governance baseline) | [CONTEXT.md](CONTEXT.md) |
| Architecture decision records (ADRs) | [docs/adr/](docs/adr/) |
| Implementation roadmap & governance planning | [docs/planning/](docs/planning/) |
| Operations handbook (in progress) | [docs/handbook/](docs/handbook/) |

---

## 📋 Changelog

Full change history (German): [CHANGELOG.md](CHANGELOG.md)
