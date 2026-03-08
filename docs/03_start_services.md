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
| `--profile` | `cpu`, `gpu-nvidia`, `gpu-amd`, `none` | `cpu` | Hardware/Ollama profile |
| `--environment` | `private`, `public` | `public` | Deployment environment |
| `--remove-volumes` | — | off | Delete all data volumes (irreversible!) |
| `--no-cleanup` | — | off | Skip container cleanup (for debugging) |

---

## Typical commands

### Mac / Apple Silicon (Ollama lokal, kein Docker-Ollama)

```bash
python3 start_services.py --profile none
```

### Mac / Apple Silicon (Ollama in Docker, CPU)

```bash
python3 start_services.py --profile cpu
```

### Nvidia GPU

```bash
python3 start_services.py --profile gpu-nvidia
```

### AMD GPU (Linux)

```bash
python3 start_services.py --profile gpu-amd
```

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

## Mac-spezifisch: Ollama lokal statt in Docker

Wenn Ollama auf dem Mac läuft (nicht in Docker), stelle sicher dass in der `.env` steht:

```bash
OLLAMA_HOST=http://host.docker.internal:11434
```

Und nach dem Start in n8n:
1. `http://localhost:5678/home/credentials` → "Local Ollama service"
2. Base URL auf `http://host.docker.internal:11434/` ändern

---

## Ohne Auth (lokale Entwicklung)

```bash
python3 start_services.py --profile none --environment private
```

Im `private`-Modus läuft kein `auth-gateway`, kein Caddy-Protected-Snippet.
Services sind direkt über `localhost:PORT` erreichbar.
