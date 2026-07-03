# 20. Ressourcen-Optimierung

Übersicht aller gesetzten Memory-Limits, Logging-Configs und Performance-Einstellungen im Stack.

---

## Memory-Limits (deploy.resources)

Alle Services haben explizite Limits. Limits sind bewusst konservativ gesetzt — bei echtem Bedarf (z.B. große Vektorkollektionen in Qdrant, viele parallele n8n-Workflows) entsprechend erhöhen.

| Service | Limit | Reservierung | Hinweis |
|---|---|---|---|
| open-webui | 2 GB | 512 MB | Whisper STT kann beim Laden kurz spiken |
| n8n | 1 GB | 256 MB | Erhöhen bei speicherintensiven Workflows |
| tts-service | 3 GB | 512 MB | Metal-Inferenz, sparsam trotz hohem Limit |
| python-nlp-service | 900 MB | 512 MB | 1 Worker, 2× spaCy-Modelle (de+en) |
| ocr-service | 4 GB | 1 GB | TrOCR-Modelle |
| grafana | 512 MB | 128 MB | |
| neo4j | 2 GB | 256 MB | optional; JVM-Heap per NEO4J_* konfigurierbar |
| qdrant | 1 GB | 256 MB | bei großen Kollektionen erhöhen |
| flowise | 1 GB | 256 MB | optional |
| langfuse-web | 1 GB | 256 MB | optional |
| langfuse-worker | 1 GB | 256 MB | optional |
| clickhouse | 2 GB | 256 MB | optional; Analytics-DB |
| minio | 512 MB | 128 MB | optional |
| postgres (Langfuse) | 512 MB | 128 MB | separater Langfuse-Postgres |
| redis (Valkey) | 256 MB | 64 MB | |
| searxng | 512 MB | 128 MB | |
| crawl4ai | 3 GB | 512 MB | optional; Chromium-basiert |
| caddy | 256 MB | 64 MB | |
| auth-gateway | 256 MB | 64 MB | |
| dashboard-ui | 128 MB | 32 MB | nginx |
| uptime-kuma | 512 MB | 128 MB | |

---

## Logging

Alle Services sind auf `json-file` mit explizitem `max-size`-Limit konfiguriert:

| Kategorie | max-size | max-file |
|---|---|---|
| Standard (Anwendungen) | 10 MB | 3 |
| Infrastruktur (Caddy, Redis, SearXNG) | 1 MB | 1 |
| Monitoring (Uptime Kuma) | 5 MB | 2 |

Ohne diese Limits können Log-Dateien auf einem Langzeit-System mehrere GB anwachsen.

---

## Kong (Supabase API-Gateway)

**Problem:** Kong startet standardmäßig mit 8 Nginx-Worker-Prozessen, was lokal ~10% CPU dauerhaft verbraucht.

**Fix** in `docker-compose.override.public.supabase.yml`:
```yaml
kong:
  environment:
    KONG_NGINX_WORKER_PROCESSES: "2"
```

Ergebnis: CPU-Last < 1%, RAM von ~490 MB auf ~145 MB gesunken.

---

## Python NLP Service

Standard-Gunicorn startet 2 Worker-Prozesse — jeder lädt beide spaCy-Modelle (de+en) separat in den RAM. Das verdoppelt den Speicherverbrauch ohne Vorteil für lokalen Einzelbetrieb.

**Fix** in `docker-compose.yml`:
```yaml
- WORKERS=1   # war: 2
- THREADS=4   # 4 Threads im Worker für Parallelität
```

Ergebnis: RAM von 1.35 GB auf 690 MB halbiert.

---

## Disk-Maintenance

```bash
# Build-Cache leeren (sicher, wird bei nächstem Build neu aufgebaut)
docker builder prune -f

# Ungenutzte Images entfernen (nur Images ohne laufende Container)
# Sicher wenn Stack läuft — genutzte Images sind geschützt
docker image prune -a -f

# Anonyme Volumes ohne Container-Referenz entfernen
docker volume prune -f

# HuggingFace-Modell-Cache (OCR-Service) leeren
# Wird beim nächsten OCR-Start automatisch neu geladen
rm -rf ocr_storage/temp/huggingface_cache/
```

> Named Volumes (`n8n_storage`, `qdrant_storage` etc.) werden von `volume prune` **nie** gelöscht — sie haben einen Namen und sind damit explizit benannt.

---

## Custom Images aktuell halten

Die vier selbst gebauten Services (`auth-gateway`, `python-nlp-service`, `ocr-service`, `tts-service`) veralten still — `docker compose up` startet immer den zuletzt gebauten Stand.

```bash
# Empfohlen: monatlich oder nach Sicherheitsmeldungen
python3 start_services.py --profile none --rebuild
```

`--rebuild` führt `docker compose build --pull --no-cache` aus: holt neue Base-Images, läuft `apt-get upgrade` durch, respektiert aber gepinnte Versionen in `requirements.txt`.

**Python-Pakete mit bekannten Risiken (Stand 2026-06):**

| Service | Paket | Installiert | Aktuell | Risiko |
|---|---|---|---|---|
| ocr-service, tts-service | `anyio` | 3.7.1 | 4.x | hoch (Major) |
| ocr-service, tts-service | `fastapi` | 0.104.1 | 0.138.x | mittel |
| tts-service | `gradio` | 5.1.0 | 6.x | hoch (Major) |
| python-nlp-service | `neo4j` | 5.27.0 | 6.x | hoch (Major, API-Breaking) |
| auth-gateway | `Flask-Limiter` | 3.9.0 | 4.x | niedrig |

Major-Version-Sprünge erst in einer Testumgebung validieren bevor die `requirements.txt` aktualisiert wird.

---

## Supabase: PG15 → PG17 Migration (ausstehend)

Das Supabase-Submodul wurde auf `postgres:17.x` aktualisiert, das lokale Daten-Volume ist aber noch PG15-initialisiert. Das Image ist in `docker-compose.override.public.supabase.yml` temporär auf `15.8.1.085` gepinnt.

Für die Migration (wenn gewünscht):
```bash
# 1. Dump mit PG15
docker exec supabase-db pg_dumpall -U postgres > dump_pg15.sql

# 2. Altes Daten-Volume löschen
docker volume rm localai_db-data   # Achtung: Daten gehen verloren

# 3. PG17-Image in Override entfernen (Pin aufheben)
# 4. Stack neu starten → initialisiert frische PG17-DB
# 5. Dump einspielen
cat dump_pg15.sql | docker exec -i supabase-db psql -U postgres
```

Siehe auch [07_troubleshooting.md](07_troubleshooting.md) für Symptome und Diagnose.
