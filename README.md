# Self-hosted AI Masterbrain 🚀

**Local AI development stack** with n8n, Supabase, Ollama, WebUI, Crawl4AI, Qdrant, and more.  
Ideal for building your own RAG workflows, data agents, and secure AI experiments – locally or in the cloud.

This is Wolf's version with a couple of improvements and the addition of Crawl4ai, NLP-Container and Dashboard with Auth. 

Also, the local RAG AI Agent workflows from the video (by Cole) will be automatically in your 
n8n instance if you use this setup instead of the base one provided by n8n!

**IMPORANT**: Supabase has updated a couple environment variables so you may have to add some new default values in your .env that I have in my .env.example if you have had this project up and running already and are just pulling new changes. Specifically, you need to add "POOLER_DB_POOL_SIZE=5" to your .env. This is required if you haves had the package running before June 14th.

## Important Links

- [Original Local AI Starter Kit](https://github.com/n8n-io/self-hosted-ai-starter-kit) by the n8n team

- [Based on the Local AI Packaged](https://github.com/coleam00/local-ai-packaged) by the coleam00 & team

- Download Cole's N8N + OpenWebUI integration [directly on the Open WebUI site.](https://openwebui.com/f/coleam/n8n_pipe/) (more instructions below)

Curated by <https://github.com/n8n-io> and <https://github.com/coleam00>, it combines the self-hosted n8n
platform with a curated list of compatible AI products and components to
quickly get started with building self-hosted AI workflows.

---

### What’s included

✅ [**Self-hosted n8n**](https://n8n.io/) - Low-code platform with over 400
integrations and advanced AI components

✅ [**New: Dashboard with Auth**] - Grid overview of all available services with 
auth when public (vps), no auth on local (work in progress)

✅ [**Supabase**](https://supabase.com/) - Open source database as a service -
most widely used database for AI agents

✅ [**Ollama**](https://ollama.com/) - Cross-platform LLM platform to install
and run the latest local LLMs

✅ [**Open WebUI**](https://openwebui.com/) - ChatGPT-like interface to
privately interact with your local models and N8N agents

✅ [**Flowise**](https://flowiseai.com/) - No/low code AI agent
builder that pairs very well with n8n

✅ [**New: Crawl4ai**](https://crawl4ai.com/) - scraping / crawling 4 LLM usage or data aggregation, screenshots, etc. 

✅ [**Python NLP / Document Service**] - Production-ready document processing container with Flask/Gunicorn. Extracts text from PDFs and images, runs OCR via **Ollama glm-ocr** (no local Tesseract needed), and performs Named Entity Recognition (NER) in German and English via SpaCy. Provides a single `/document/analyze` endpoint that returns text + entities in one call – ideal as preprocessing pipeline for Neo4j Knowledge Graphs and n8n workflows.

✅ [**Qdrant**](https://qdrant.tech/) - Open source, high performance vector
store with an comprehensive API. Even though you can use Supabase for RAG, this was
kept unlike Postgres since it's faster than Supabase so sometimes is the better option.

✅ [**Neo4j**](https://neo4j.com/) - Knowledge graph engine that powers tools like GraphRAG, LightRAG, and Graphiti 

✅ [**SearXNG**](https://searxng.org/) - Open source, free internet metasearch engine which aggregates 
results from up to 229 search services. Users are neither tracked nor profiled, hence the fit with the local AI package.

✅ [**Caddy**](https://caddyserver.com/) - Managed HTTPS/TLS for custom domains

✅ [**Langfuse**](https://langfuse.com/) - Open source LLM engineering platform for agent observability

---

## 🌟 Features

- ✅ Local or server hosted Ollama and/or public LLMs
- ✅ Authenticated dashboard access (Caddy)
- ✅ Supabase with vector store & authentication
- ✅ Crawl4AI, Qdrant, Neo4j, Langfuse, Python NLP/Document Service (OCR + NER, DE+EN), MinIO, Open WebUI, ...
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
cp .env.example .env 	# !! Edit the .env and fill the secrets
python start_services.py --profile cpu  # see "03_start_script.md" for more profiles, eg. For MacOS
```

👉 n8n: http://localhost:5678/  
👉 Open WebUI: http://localhost:3000/

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
| Links & resources        | [tips_links.md](docs/tips_links.md) |

---

## 📋 Changelog

### 2026-03 – Python NLP/Document Service v2.0

**`python-nlp-service/` – OCR + multilingual NER**

| Komponente | Alt | Neu |
|-----------|-----|-----|
| Funktion | Nur deutsches NER | NER (DE+EN) + OCR + PDF-Extraktion |
| SpaCy-Modelle | `de_core_news_md` | `de_core_news_md` + `en_core_web_md` |
| OCR | — | Via Ollama `glm-ocr` (konfigurierbar via `OCR_MODEL`) |
| PDF-Extraktion | — | PyMuPDF (direkt + OCR-Fallback für gescannte PDFs) |
| Neuer Haupt-Endpoint | — | `POST /document/analyze` (Text + Entities in einem Call) |
| Compat-Endpoints | — | `/pdf/extract`, `/pdf/analyze-type`, `/pdf/to-png-smart` |
| RAM-Limit | 1 GB | 1.5 GB (zwei SpaCy-Modelle) |
| Neue Env-Variablen | — | `OLLAMA_HOST`, `OCR_MODEL` |
| extra_hosts | — | `host.docker.internal:host-gateway` (Linux-Kompatibilität) |
| n8n depends_on | auskommentiert | aktiv (`service_healthy`) |

---

### 2026-02 – Dependency Updates

**Python packages updated to latest (CVE-clean, verified via OSV.dev)**

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

**Supabase Submodule-Pointer aktualisiert**

| Komponente | Alt | Neu |
|-----------|-----|-----|
| Pointer | `169e3d9` | `571e060` |
| supabase-studio | 2025.11.10 | **2026.02.16** |
| gotrue (auth) | v2.182.1 | **v2.186.0** |
| postgrest | v13.0.7 | **v14.5** ⚠️ Major |
| realtime | v2.63.0 | **v2.76.5** |

---

### 2026-02 – Docker Compose & Infrastructure

**`docker-compose.yml` – Bug fixes & improvements**

| Prio | Service | Was | Fix |
|------|---------|-----|-----|
| 🔴 Bug | `python-nlp-service` | Healthcheck testete Port `5050` statt `5000` – Container wurde permanent als `unhealthy` markiert | Port korrigiert |
| 🟠 Stability | `open-webui` | Image-Tag `:main` (Development Branch, instabil) | → `:latest` |
| 🟠 Correctness | `python-nlp-service` | `FLASK_ENV=production` seit Flask 2.2 deprecated, bei Gunicorn-Betrieb wirkungslos | Variable entfernt |
| 🟠 Ops | `python-nlp-service`, `neo4j` | `restart: always` startet Container auch nach manuellem `docker stop` neu | → `unless-stopped` |
| 🟠 Ops | `n8n`, `python-nlp-service`, `open-webui`, `neo4j` | Keine Log-Rotation konfiguriert, Logs können unkontrolliert wachsen | `json-file` Driver mit `max-size: 10m / max-file: 3` |
| 🟡 Usability | `neo4j` | Kein `container_name`, kein Healthcheck | `container_name: neo4j` + HTTP-Check auf Port 7474 |

**`start_services.py` – Bug fix**

| Prio | Funktion | Was | Fix |
|------|----------|-----|-----|
| 🔴 Bug | `check_and_fix_docker_compose_for_searxng()` | SearXNG `cap_drop`-Fix suchte nach `"cap_drop: - ALL"` als Einzeiler, YAML enthält aber Multi-Line-Format (`cap_drop:\n  - ALL`) → Bedingung war immer `False`, SearXNG konnte beim ersten Start fehlschlagen | Suchstring auf korrektes Multi-Line-Format geändert, eindeutig über nachfolgendes `cap_add: CHOWN` |

---

### 2026-02 – Python NLP Service

**`python-nlp-service/` – Versions-Update & Optimierung**

| Component | Before | After | Hinweis |
|-----------|--------|-------|---------|
| Python | 3.11 | **3.12** | |
| SpaCy model | `de_core_news_sm` (~13 MB) | **`de_core_news_md`** (~43 MB) | Bessere NER-Qualität, kein GPU nötig |
| NumPy | 1.26.x | **2.2.x** | Breaking Changes zu 1.x; SpaCy 3.8.x und pandas 2.2.x kompatibel |
| Flask | 3.0.0 | **3.1.0** | |
| Gunicorn | 21.2.0 | **23.0.0** | |
| spaCy | 3.7.5 | **3.8.3** | |
| pandas | 2.1.4 | **2.2.3** | |
| requests | 2.31.0 | **2.32.3** | |
| python-json-logger | 2.0.7 | **3.0.0** | |
| Dockerfile-Struktur | Site-packages direkt kopiert | **Virtual Environment** `/opt/venv` | Saubere Isolation, kein versehentliches Mitkopieren von Build-Tools |
| Sicherheit | Root-User, keine feste UID | **Non-root UID 1001** | |
| Monitoring | Kein Docker-HEALTHCHECK | **`HEALTHCHECK`** über `/health` Endpoint | |
| OCR | — | Über **Ollama** (nicht in diesem Container) | |

---

### 2026-02 – Security Hardening & Improvements

**`auth-gateway/` – Vollständige Sicherheitshärtung**

| Prio | Komponente | Was | Fix |
|------|-----------|-----|-----|
| 🔴 Sicherheit | `Dockerfile` | Root-User, kein multi-stage Build, keine feste UID, kein `HEALTHCHECK`, kein `apt-get upgrade` | Multi-stage Build + Virtual Environment `/opt/venv`, Non-root UID 1002, `HEALTHCHECK`, `apt-get upgrade` |
| 🔴 Sicherheit | `app.py` | Sensitive Token-Daten wurden in Logs geschrieben → potenzielle Credential-Exposition | Sensible Daten vollständig entfernt; generische Warning-Message |
| 🟠 Stability | `app.py` | Kein `/health`-Endpoint → `HEALTHCHECK` und Monitoring nicht möglich | `/health`-Endpoint hinzugefügt |
| 🟠 Versions | `requirements.txt` | `flask==3.0.0`, `gunicorn==21.2.0`, `supabase==2.4.2` (>1 Jahr alt) | `flask==3.1.0`, `gunicorn==23.0.0`, `supabase==2.28.0` |

**`python-nlp-service/app.py` – DoS-Schutz**

| Prio | Komponente | Was | Fix |
|------|-----------|-----|-----|
| 🔴 Sicherheit | `/process` Endpoint | Keine Eingabegrößenbeschränkung → beliebig große Texte möglich (DoS) | Maximale Eingabegröße begrenzt; HTTP 413 bei Überschreitung |

**`Caddyfile` – Security Headers**

| Prio | Komponente | Was | Fix |
|------|-----------|-----|-----|
| 🟠 Sicherheit | Alle vHosts | Keine Security Headers konfiguriert | `(security_headers)`-Snippet mit HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy, `-Server` in allen aktiven vHosts |

**`backup.sh` – .env Backup**

| Prio | Komponente | Was | Fix |
|------|-----------|-----|-----|
| 🟠 Ops | `.env` | Konfigurationsdatei mit Secrets wurde nicht gesichert | `.env` wird mit `chmod 600` ins Backup-Verzeichnis kopiert |

**`docker-compose.yml` – crawl4ai Ressourcenlimits**

| Prio | Komponente | Was | Fix |
|------|-----------|-----|-----|
| 🟠 Stability | `crawl4ai` | Keine Ressourcenlimits, kein Healthcheck | Memory-Limit 3 GB (Reservation 512 MB), `HEALTHCHECK` auf `/health` Port 11235 |

**`dashboard/index.html` – CDN Subresource Integrity**

| Prio | Komponente | Was | Fix |
|------|-----------|-----|-----|
| 🟡 Supply Chain | `supabase-js` CDN | Floating-Tag `@2` ohne SRI-Hash → CDN-Kompromittierung möglich | Gepinnte Version `@2.97.0` + `integrity="sha384-..."` + `crossorigin="anonymous"` |

**CVE-Scan (`pip-audit` + OSV.dev) – Versionskorrektur**

| CVE/GHSA | Paket | Betroffen | Fix | Beschreibung |
|----------|-------|-----------|-----|--------------|
| CVE-2025-47278 | `flask` | 3.1.0 | **3.1.1** | Signing-Key-Reihenfolge invertiert → falscher Key zum Signieren verwendet |
| GHSA-9hjg-9r4m-mvj7 | `requests` | 2.32.3 | **2.32.4** | `.netrc`-Credentials-Leak über manipulierte URLs |
| GHSA-hgf8-39gv-g3f2 | `werkzeug` | 3.1.3 | **3.1.5** | `safe_join()` erlaubt Windows-Sondergerätenamen |
| GHSA-87hc-h4r5-73f7 | `werkzeug` | 3.1.3 | **3.1.5** | `safe_join()` erlaubt Sondergerätenamen mit zusammengesetzten Endungen |

Fixes angewendet in `auth-gateway/requirements.txt` und `python-nlp-service/requirements.txt`.

---

📜 License: Apache 2.0 – see [LICENSE](LICENSE)

---

### 2026-03 – Upstream Sync (coleam00/local-ai-packaged)

Selektive Übernahme von 13 Upstream-Commits. Unsere Ergänzungen (auth-gateway, dashboard, docs, python-nlp-service) bleiben vollständig erhalten.

| Was | Upstream-Commit | Übernahme |
|---|---|---|
| `n8n-import`-Service entfernt | `48c186a`, `8d02114` | ✅ Service + `depends_on`-Eintrag entfernt |
| n8n `LocalFileTrigger` + `ExecuteCommand` aktivierbar | `ce882b7` | ✅ `NODES_EXCLUDE`-Kommentar in x-n8n hinzugefügt |
| Neue Supabase Storage Env-Vars | `57c194a` | ✅ In `.env.example` ergänzt |
| Neue n8n Workflow-Dateien (V1/V2/V3 RAG Agent) | `5c55af2` | ✅ In `n8n/backup/workflows/` kopiert |
| shared-Volume-Pfad: `:/home/node/.n8n-files/shared` → `:/data/shared` | `8d02114` | ✅ Übernommen |
| `LANGFUSE_ENCRYPTION_KEY` → `ENCRYPTION_KEY` | — | ✅ In `docker-compose.yml` + `.env.example` |
| Caddy-Hostnames ohne `${DOMAIN}` | — | ⏭️ Nicht übernommen (unser Setup nutzt `${DOMAIN}`) |
| `open-webui:latest` → `:main` | — | ⏭️ Nicht übernommen (`:latest` stabiler) |
| `crawl4ai` entfernt | — | ⏭️ Nicht übernommen (Teil unseres Stacks) |
| `neo4j` restart: always, kein Healthcheck | — | ⏭️ Nicht übernommen (unser Healthcheck behalten) |
