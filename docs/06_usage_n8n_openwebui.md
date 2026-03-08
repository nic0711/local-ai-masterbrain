# 6. Nutzung: n8n, Open WebUI & weitere Services

## Zugriff (lokal)

Alle Services sind nach dem Login unter `https://brain.local` erreichbar.
Das Dashboard verlinkt direkt auf alle Services.

| Service       | URL                          |
|---------------|------------------------------|
| Dashboard     | https://brain.local          |
| n8n           | https://n8n.brain.local      |
| Open WebUI    | https://webui.brain.local    |
| Flowise       | https://flowise.brain.local  |
| Langfuse      | https://langfuse.brain.local |
| SearXNG       | https://search.brain.local   |
| Neo4j         | https://neo4j.brain.local    |
| Qdrant        | https://qdrant.brain.local   |
| Minio         | https://minio.brain.local    |

---

## n8n einrichten

1. `https://n8n.brain.local` aufrufen (nach Login im Dashboard automatisch zugänglich)
2. Credentials für die verwendeten Services anlegen:

   | Service | Verbindung |
   |---|---|
   | Ollama | `http://ollama:11434` (Docker) oder `http://host.docker.internal:11434` (lokal) |
   | Supabase DB | Host: `db`, Port: `5432`, DB/User/PW aus `.env` |
   | Qdrant | `http://qdrant:6333` |

3. Workflows importieren: **Settings → Import workflow** → JSON-Dateien aus `n8n/backup/workflows/`

### LocalFileTrigger & ExecuteCommand aktivieren

Diese Nodes sind in n8n v2+ standardmäßig deaktiviert. In `docker-compose.yml` unter `x-n8n` einkommentieren:

```yaml
- NODES_EXCLUDE=[]
```

Dann n8n neu starten: `docker compose -p localai restart n8n`

---

## Open WebUI einrichten

1. `https://webui.brain.local` aufrufen
2. n8n-Pipe-Funktion einrichten:
   - **Workspace → Functions → Add Function**
   - Code aus `n8n_pipe.py` einfügen
   - Gear-Icon → `n8n_url` auf den Produktions-Webhook-URL setzen
3. Funktion aktivieren → in der Modell-Auswahl verfügbar

---

## Stack upgraden

```bash
# Services stoppen
docker compose -p localai down

# Neueste Images pullen
docker compose -p localai -f docker-compose.yml pull

# Stack neu starten
python3 start_services.py --profile <dein-profil>
```

> `start_services.py` allein pullt keine neuen Images – `docker compose pull` ist dafür nötig.

---

## Ollama-Modelle hinzufügen

```bash
# Wenn Ollama im Docker-Container läuft:
docker exec ollama ollama pull llama3.2

# Wenn Ollama lokal auf dem Mac läuft:
ollama pull llama3.2
```

Modelle sind danach sofort in Open WebUI und n8n verfügbar.
