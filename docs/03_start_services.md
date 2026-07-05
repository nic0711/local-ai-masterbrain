# 3. Start Script: `start_services.py`

The `start_services.py` script handles the complete lifecycle of the stack.

### What it does

1. Updates Supabase repo & copies `.env`
2. Stops all running containers, removes orphans
3. Waits for ports to be released
4. Starts Supabase first, then the AI stack
5. Checks service health

Volumes are safe by default unless `--remove-volumes` is passed.

---

## Arguments

| Argument | Options | Default | Description |
|---|---|---|---|
| `--profile` | `cpu`, `gpu-nvidia`, `gpu-amd`, `none` | `cpu` | Optionale Hardware-Profile (Ollama läuft standardmäßig auf dem Host) |
| `--environment` | `private`, `public` | `public` | Deployment environment |
| `--rebuild` | — | off | Custom Images vor Start neu bauen (Base-Images + OS-Pakete aktualisieren) |
| `--remove-volumes` | — | off | Delete all data volumes (irreversible!) |
| `--no-cleanup` | — | off | Skip container cleanup (for debugging) |

---

## Typical commands

### Mac / Apple Silicon (Standard – Ollama läuft lokal)

```bash
python3 start_services.py
# oder explizit:
python3 start_services.py --profile none
```

Ollama wird **nicht** als Docker-Container gestartet. Alle Services (`n8n`, `tts-service` etc.) verbinden sich über `http://host.docker.internal:11434` mit dem lokal laufenden Ollama-Prozess.

### Nvidia GPU

```bash
python3 start_services.py --profile gpu-nvidia
```

### AMD GPU (Linux)

```bash
python3 start_services.py --profile gpu-amd
```

### Ollama als Docker-Container (fortgeschritten)

Für Deployments ohne lokales Ollama (z.B. rein containerisierter Linux-Server):

```bash
# Stack starten + Ollama als Container hinzufügen
docker compose --profile ollama-docker up -d
```

> **Hinweis:** `start_services.py` unterstützt `--profile ollama-docker` nicht direkt. Für diesen Fall Docker Compose direkt verwenden.

---

## `--environment` erklärt

| Wert | Zweck |
|---|---|
| `public` *(default)* | Standard – nur Port 80/443 offen, alle Services hinter Caddy + JWT-Auth |
| `private` | Lokale Entwicklung ohne Auth – viele Ports direkt erreichbar |

`--environment public` aktiviert automatisch:
- Caddy als Reverse Proxy mit HTTPS
- `auth-gateway` (JWT-Validierung für alle geschützten Services)
- TOTP/2FA-Unterstützung in Supabase GoTrue
- Cookie-basierte Auth für Cross-Subdomain-Zugriff

> **Lokal mit Auth:** `--environment public` funktioniert auch lokal mit `brain.local` als Domain (Self-Signed Cert von Caddy). Siehe [02_configuration.md](02_configuration.md).

---

## Ollama: lokal vs. Docker

**Standard-Setup (Mac):** Ollama läuft nativ auf dem Host. Alle Services verwenden `http://host.docker.internal:11434` – kein Container nötig, keine `--profile`-Angabe erforderlich.

In n8n die Ollama-Credential prüfen:
1. `http://localhost:5678/home/credentials` → "Local Ollama service"
2. Base URL muss `http://host.docker.internal:11434/` sein

**Ollama als Container:** `docker compose --profile ollama-docker up -d` startet alle drei Varianten (CPU, GPU-Nvidia, GPU-AMD) plus den Init-Container, der Standardmodelle pullt. In diesem Fall muss die Ollama-Credential in n8n auf `http://ollama:11434/` zeigen.

---

## Ohne Auth (lokale Entwicklung)

```bash
python3 start_services.py --profile none --environment private
```

Im `private`-Modus läuft kein `auth-gateway`, kein Caddy-Protected-Snippet.
Services sind direkt über `localhost:PORT` erreichbar.

---

## Images aktuell halten (`--rebuild`)

Der Stack enthält vier selbst gebaute Images:
`auth-gateway` · `python-nlp-service` · `ocr-service` · `tts-service`

Diese werden **nicht automatisch aktualisiert** — `docker compose up` startet immer den zuletzt gebauten Stand. Mit `--rebuild` werden alle vier Images neu gebaut, bevor der Stack startet:

```bash
python3 start_services.py --profile none --rebuild
```

Was `--rebuild` macht:
- `docker compose build --pull --no-cache` für alle vier Custom-Services
- `--pull` holt das neueste Base-Image (`python:3.12-slim-bookworm` etc.)
- `--no-cache` läuft `apt-get upgrade` frisch durch → OS-Security-Patches
- Gepinnte Versionen in `requirements.txt` werden **respektiert** — kein unkontrolliertes `pip upgrade`

**Empfehlung:** Monatlich oder nach Sicherheitsmeldungen ausführen. Dauert ca. 5–10 Minuten (Download + Build).

### Python-Abhängigkeiten aktualisieren

Für gezielte Paket-Updates `requirements.txt` manuell anpassen und dann `--rebuild` ausführen. Major-Version-Sprünge (z.B. `neo4j` 5→6, `gradio` 5→6) immer separat testen — sie können Breaking Changes enthalten.

```bash
# Veraltete Pakete in einem laufenden Container anzeigen
docker exec python-nlp-service pip list --outdated
docker exec auth-gateway pip list --outdated
```

---

## Optionale Services

Bestimmte ressourcenintensive Services starten **nicht automatisch** (`profiles: [optional]` oder `profiles: [monitoring]`):

**optional:** `neo4j` · `flowise` · `minio` · `clickhouse` · `langfuse-web` · `langfuse-worker` · `crawl4ai` · `hermes-gateway` · `hermes-dashboard` · `odysseus` · `chromadb-odysseus`

**monitoring:** `prometheus` · `node-exporter` · `cadvisor` · `pushgateway` · `mqtt2prometheus` · `modbus-exporter`

Autostart für Odysseus und Hermes: `AUTOSTART_ODYSSEUS=true` / `AUTOSTART_HERMES=true` in `.env`.

`start_services.py` übergibt beim **Down** automatisch `--profile optional`, damit diese Services beim Neustart ebenfalls sauber gestoppt werden.

Start auf Abruf: Dashboard → Admin-Tab → Service Control, oder per API:
```bash
curl -X POST https://brain.local/_control/services/neo4j/start \
  -H "Authorization: Bearer $TOKEN"
```

Siehe [19_on_demand_services.md](19_on_demand_services.md) für Details.
