# Self-hosted AI Masterbrain 🚀

**Local AI Development Stack** mit n8n, Supabase, Ollama, WebUI, Crawl4AI, Qdrant u.v.m.  
Ideal für eigene RAG-Workflows, Datenagenten und sichere AI-Experimente – lokal oder in der Cloud.

---

## 🌟 Features

- ✅ Lokales Ollama + LLMs
- ✅ Authentifizierter Dashboard-Zugriff (Caddy)
- ✅ Supabase mit Vektorspeicher & Auth
- ✅ Crawl4AI, Qdrant, Neo4j, Langfuse
- ✅ Automatisierter Start & Cleanup via `start_services.py`

---

## 🔧 Schnellstart

```bash
git clone -b stable https://github.com/nic0711/local-ai-masterbrain
cd local-ai-masterbrain
cp .env.example .env
python start_services.py --profile cpu
```

👉 n8n: http://localhost:5678/  
👉 Open WebUI: http://localhost:3000/

---

## 📚 Dokumentation

| Thema                     | Datei                                   |
|--------------------------|------------------------------------------|
| Installation             | [01_installation.md](docs/01_installation.md) |
| Konfiguration (.env)     | [02_configuration.md](docs/02_configuration.md) |
| Start-Skript (Details)   | [03_start_services.md](docs/03_start_services.md) |
| Cloud Deployment         | [04_cloud_deployment.md](docs/04_cloud_deployment.md) |
| Sicherheit & Hardening   | [05_security_hardening.md](docs/05_security_hardening.md) |
| Nutzung: n8n & WebUI     | [06_usage_n8n_openwebui.md](docs/06_usage_n8n_openwebui.md) |
| Fehlerbehebung           | [07_troubleshooting.md](docs/07_troubleshooting.md) |
| Backup & Wiederherstellung | [08_backup_and_recovery.md](docs/08_backup_and_recovery.md) |
| FAQ & Tipps              | [09_faq.md](docs/09_faq.md) |
| Links & Ressourcen       | [tips_links.md](docs/tips_links.md) |

📜 Lizenz: Apache 2.0 – siehe [LICENSE](LICENSE)
