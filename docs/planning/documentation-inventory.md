# Dokumentationsinventar

> Phase-1-Stand. Erstellt im Rahmen von `agent/phase-1-governance-ci-supply-chain`.
> Zweck: vollständige Bestandsaufnahme der zum Zeitpunkt dieses PR vorhandenen Dokumentation,
> als Grundlage für die spätere Handbuchkonsolidierung (Phase 8 laut
> `docs/planning/implementation-roadmap.md`). Es wird in diesem PR **nichts** aus dieser Liste
> gelöscht, zusammengeführt oder inhaltlich umgeschrieben — nur inventarisiert.

Spalten: **Status** = gültig / teilweise gültig / veraltet / widersprüchlich (bezogen auf den
tatsächlichen Repo-Zustand zum Zeitpunkt dieses PR). **Aktion** = übernehmen / überarbeiten /
zusammenführen / archivieren / entfernen (Vorschlag für die spätere Handbuchkonsolidierung,
keine Umsetzung in diesem PR).

## Root

| Datei | Zweck | Status | Zielkapitel (Handbuch, Vorschlag) | Aktion | Links/Abhängigkeiten |
|---|---|---|---|---|---|
| `README.md` | Zweisprachige (DE/EN) Projektübersicht: Praxisbeispiele, Service-Liste, Quickstart, Doku-Tabelle, Changelog | gültig, in diesem PR additiv um Architektur-/Governance-Verweise ergänzt | — (bleibt Einstiegspunkt, kein Handbuch-Kapitel) | übernehmen | verlinkt alle `docs/*.md`-Dateien; Changelog referenziert CodeQL-Fixes ohne zugehörige Workflow-Datei im Repo (Governance-Lücke, wird durch diesen PR mit `ci.yml`/Secret-Scanning teilweise adressiert, CodeQL selbst bleibt GitHub-Default-Setup) |
| `TIPPS.md` | Schritt-für-Schritt-Anleitung Supabase-Docker-Integration | teilweise gültig (Anleitung deckt manuellen Ersteinbau ab, `start_services.py` automatisiert das inzwischen weitgehend) | Installation & Betrieb | überarbeiten/zusammenführen mit `docs/01_installation.md` | überschneidet sich mit `docs/01_installation.md`, `start_services.py` |
| `CLAUDE.md` (lokal, nicht versioniert) | Projektinstruktionen für KI-Agenten | teilweise veraltet (nennt "17 Dokumentationsdateien", tatsächlich 27) | — (bleibt bewusst außerhalb der Versionierung, s. PR-Begründung) | nicht Teil dieses PR | siehe PR-Begründung zu `.gitignore`/`CLAUDE.md` |

## docs/ (27 Dateien)

| Datei | Zweck | Status | Zielkapitel (Handbuch, Vorschlag) | Aktion |
|---|---|---|---|---|
| `01_installation.md` | Voraussetzungen, Repo klonen, `.env` anlegen, `/etc/hosts`-Einträge | gültig | Installation & Betrieb | übernehmen |
| `02_configuration.md` | `.env`-Konfiguration, Secret-Generierung, Pflichtfelder n8n/Supabase | gültig | Installation & Betrieb | übernehmen |
| `03_start_services.md` | `start_services.py`-Lifecycle: Argumente, Profile, typische Befehle | gültig | Installation & Betrieb | übernehmen |
| `04_cloud_deployment.md` | Cloud/VPS-Deployment, Firewall, DNS, iptables-Härtung | gültig | Installation & Betrieb | übernehmen |
| `05_security_hardening.md` | Auth-Architektur (Caddy→auth-gateway→Supabase), Cookie-Sicherheit, 2FA/RBAC | gültig | Sicherheit | übernehmen; überschneidet sich künftig mit neuen `docs/handbook/06-secrets-und-zertifikate.md` (ADR-0010-Bezug) |
| `06_usage_n8n_openwebui.md` | Nutzung nach Login, n8n-Credentials-Setup | gültig | Nutzung | übernehmen |
| `07_troubleshooting.md` | Fehlerbehebung, Log-Befehle, Redirect-Loops | gültig | Troubleshooting | übernehmen |
| `08_backup_and_recovery.md` | Dashboard-integriertes Backup-System | gültig | Betrieb (Updates & Rollback) | übernehmen; wird von neuem `docs/handbook/04-updates-und-rollback.md` referenziert, nicht dupliziert |
| `09_faq.md` | FAQ: Erstbenutzer, Passwort-Reset, 2FA | gültig | Nutzung | übernehmen |
| `10_python_nlp_service.md` | NLP-Service: OCR via Ollama, PDF-Extraktion, NER, API | gültig | Services-Referenz | übernehmen |
| `11_obsidian_integration.md` | Obsidian-Anbindung via Local-REST-API-Plugin | gültig | Services-Referenz | übernehmen |
| `12_monitoring.md` | Uptime Kuma Service-Monitoring | gültig | Betrieb | übernehmen; Themenüberschneidung mit `23_monitoring.md` (unterschiedliche Tools: Uptime Kuma vs. Prometheus) — bei Konsolidierung zusammenführen |
| `13_graphrag.md` | GraphRAG/Neo4j Knowledge-Graph-Architektur | gültig | Services-Referenz | übernehmen |
| `14_ocr_service.md` | Eigenständiger `ocr-service` (FastAPI, TrOCR+Tesseract) | gültig | Services-Referenz | übernehmen |
| `15_api_reference.md` | Vollständige API-Referenz aller 4 Custom Services | gültig | Services-Referenz | übernehmen |
| `16_scraping_configurator.md` | n8n-Workflow "Scraping Configurator" (Crawl4AI) | gültig | Workflows | übernehmen |
| `17_dashboard_changes.md` | Dashboard-Architektur (vanilla-JS SPA) | gültig | Services-Referenz | übernehmen |
| `18_tts_service.md` | `tts-service`: TTS/Voice-Cloning/Dubbing | gültig; **Hinweis:** Service hat laut Phase-1-Prüfung keine automatisierten Tests (s. `docs/planning/test-coverage-gaps.md`) | Services-Referenz | übernehmen |
| `19_on_demand_services.md` | On-Demand-Steuerung optionaler Services über Compose-Profile | gültig | Betrieb | übernehmen |
| `20_resource_optimization.md` | Memory-Limits/Reservierungen, Logging-Konfiguration | gültig | Betrieb | übernehmen |
| `21_hermes_agent.md` | Hermes Agent (Submodul) Architektur/Start | gültig | Services-Referenz | übernehmen |
| `23_monitoring.md` | Prometheus-Stack (Prometheus, node-exporter, cAdvisor, Pushgateway) | gültig | Betrieb | übernehmen; s. Hinweis bei `12_monitoring.md` |
| `24_sps_monitoring.md` | SPS/PLC-Monitoring (MQTT/Modbus/OPC-UA) | gültig | Services-Referenz | übernehmen |
| `25_teams_bot.md` | Teams-Bot + Asana-Integration | gültig | Workflows | übernehmen |
| `26_osticket_ki.md` | osTicket-KI-Integration (n8n + Ollama + Qdrant) | gültig | Workflows | übernehmen |
| `27_knowledge_base.md` | Wissensdatenbank-Ingest-Workflows (Qdrant + Neo4j) | gültig | Workflows | übernehmen |
| `tips_links.md` | Reine externe Linkliste | gültig, aber minimal (5 Links) | Anhang | zusammenführen mit `TIPPS.md`-Linkbestand oder als Anhang übernehmen |

**Bekannte Auffälligkeit (kein Fehler, nur zu vermerken):** Nummerierungslücke bei `22_*.md` — springt von `21_hermes_agent.md` auf `23_monitoring.md`. Ursache im Repo-Verlauf nicht dokumentiert; keine Aktion in diesem PR, für Phase-8-Konsolidierung vormerken.

## docs/agents/ — nicht Teil dieses Branches

`docs/agents/domain.md` und `docs/agents/issue-tracker.md` existieren **nicht** auf `main` (Basis dieses PR), sondern ausschließlich auf dem separaten, noch offenen PR #72 (`docs/agent-skills-setup` → `main`). Dieser PR fasst sie **nicht an** und dupliziert sie nicht. Sobald PR #72 gemerged ist, referenzieren beide Dateien laut ihrem eigenen Inhalt bereits `CONTEXT.md`/`docs/adr/` am Repo-Root — das deckt sich mit den in diesem PR neu hinzugefügten Pfaden, ein Folge-Abgleich nach Merge beider PRs wird empfohlen, ist aber kein Blocker für diesen PR.

## Neu in diesem PR (zur Vollständigkeit, nicht Teil des "Alt-Bestands")

`CONTEXT.md`, `docs/adr/0001…0010-*.md`, `docs/planning/implementation-roadmap.md`, `docs/planning/documentation-inventory.md` (diese Datei), `docs/handbook/04-updates-und-rollback.md`, `docs/handbook/06-secrets-und-zertifikate.md`, `docs/handbook/09-verantwortlichkeiten.md`, `docs/planning/github-manual-settings.md`, `docs/planning/image-pinning-baseline.yml`, `docs/planning/security-exceptions/`, `docs/planning/test-coverage-gaps.md`.
