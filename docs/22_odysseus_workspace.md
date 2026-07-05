# 22. Odysseus AI Workspace

Odysseus ist ein selbst gehosteter AI-Workspace für Deep Research, Dokumentenarbeit und Team-Kollaboration. Im Stack läuft er als optionaler Service hinter Caddy-Auth.

URL: `https://workspace.brain.local`

---

## Setup

### 1. Submodul initialisieren

```bash
git submodule update --init odysseus
```

### 2. Umgebungsvariablen in `.env` setzen

```bash
ODYSSEUS_HOSTNAME=workspace.brain.local
ODYSSEUS_ADMIN_USER=admin
ODYSSEUS_ADMIN_PASSWORD=$(openssl rand -hex 24)
ODYSSEUS_UID=1000
ODYSSEUS_GID=1000
ODYSSEUS_EMBEDDING_MODEL=nomic-embed-text

# Optional: OpenRouter als LLM-Fallback
OPENROUTER_API_KEY=sk-or-...

# Optional: Autostart bei Stack-Start
AUTOSTART_ODYSSEUS=false
```

### 3. Image bauen (erster Start ~5–10 min)

```bash
docker compose -p localai --profile optional build odysseus
```

### 4. Starten

**Über Dashboard-Macro:** „Odysseus starten" klicken → startet ChromaDB + Odysseus.

**Oder manuell:**
```bash
docker compose -p localai --profile optional up -d chromadb-odysseus odysseus
```

### 5. Erster Login

1. `https://workspace.brain.local` aufrufen
2. Mit `ODYSSEUS_ADMIN_USER` + `ODYSSEUS_ADMIN_PASSWORD` anmelden
3. Team-User im Odysseus-Admin-Panel anlegen

---

## Architektur im Stack

```
Browser → Caddy (forward_auth → auth-gateway) → odysseus:7000
                                                    │
                                          chromadb-odysseus:8000
                                          searxng:8080 (geteilt)
                                          Ollama (host.docker.internal:11434)
```

**Wichtig:** Caddy schützt den Zugang via Supabase-JWT. Nur eingeloggte Nutzer kommen rein. Innerhalb von Odysseus gibt es eine eigene User-Verwaltung – Superadmin legt Odysseus-Admin-Account an, Team-Members erhalten normale Odysseus-Accounts.

---

## LLM-Konfiguration

### Primär: lokales Ollama

Standardmäßig zeigt Odysseus auf `http://host.docker.internal:11434/v1` (lokales Ollama auf dem Host-Mac).

Empfohlene Modelle (via `ollama pull`):
- `qwen2.5:7b` – General Purpose
- `qwen2.5:14b` – Bessere Qualität, mehr RAM
- `nomic-embed-text` – Embedding (Pflicht für ChromaDB-Suche)

### Fallback: OpenRouter

Wenn `OPENROUTER_API_KEY` gesetzt ist, wird er als `OPENAI_API_KEY` an Odysseus übergeben. In Odysseus unter Einstellungen → Modelle → OpenAI-kompatibler Endpoint:
- URL: `https://openrouter.ai/api/v1`
- Key: dein OpenRouter-Key

---

## SearXNG-Integration

Odysseus nutzt **unsere bestehende SearXNG-Instanz** (`http://searxng:8080`), nicht eine eigene. Das spart ~200MB RAM. Kein separater SearXNG-Container nötig.

---

## ChromaDB

Odysseus hat einen eigenen `chromadb-odysseus` Container für seine internen Vektordaten (Memories, RAG-Dokumente). Dieser ist getrennt von Qdrant, das der Rest des Stacks für n8n-Workflows nutzt.

---

## Autostart

In `.env`:
```bash
AUTOSTART_ODYSSEUS=true   # startet chromadb-odysseus + odysseus beim Stack-Start
AUTOSTART_HERMES=true     # startet hermes-gateway + hermes-dashboard beim Stack-Start
```

`start_services.py` liest diese Variablen und startet die Services nach dem regulären `compose up`.

---

## Updates

Odysseus ist als Git-Submodul eingebunden (Commit-Pointer fixiert):

```bash
cd odysseus && git fetch && git checkout <neuer-commit>
cd ..
docker compose -p localai --profile optional build odysseus
docker compose -p localai restart odysseus
git add odysseus && git commit -m "chore(odysseus): update to <version>"
```

---

## Troubleshooting

| Problem | Lösung |
|---|---|
| Build schlägt fehl | `docker compose build --no-cache odysseus` |
| `workspace.brain.local` nicht erreichbar | `docker compose logs odysseus` prüfen, ob Port 7000 läuft |
| Login schlägt fehl | Caddy-Cookie prüfen: `brain.local/login.html` → Login → dann Workspace aufrufen |
| ChromaDB nicht verfügbar | `docker compose ps chromadb-odysseus` – muss running sein bevor Odysseus startet |
| Embedding fehlt | `ollama pull nomic-embed-text` auf dem Host ausführen |
