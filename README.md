# Self-hosted AI Masterbrain 🚀

**Local AI development stack** with n8n, Supabase, Ollama, WebUI, Crawl4AI, Qdrant, and more.  
Ideal for building your own RAG workflows, data agents, and secure AI experiments – locally or in the cloud.

This is Wolf's version with a couple of improvements and the addition of Crawl4ai, NLP-Container and Dashboard with Auth. 

Also, the local RAG AI Agent workflows from the video (by Cole) will be automatically in your 
n8n instance if you use this setup instead of the base one provided by n8n!

**IMPORANT**: Supabase has updated a couple environment variables so you may have to add some new default values in your .env that I have in my .env.example if you have had this project up and running already and are just pulling new changes. Specifically, you need to add "POOLER_DB_POOL_SIZE=5" to your .env. This is required if you have had the package running before June 14th.

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

✅ [**New: Python NLP Container**] - special container for python tools like flask, spyCy, pandas, and more

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
- ✅ Crawl4AI, Qdrant, Neo4j, Langfuse, Python NLP, MimIO, Open WebUI, ...
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
| Links & resources        | [tips_links.md](docs/tips_links.md) |

📜 License: Apache 2.0 – see [LICENSE](LICENSE)
