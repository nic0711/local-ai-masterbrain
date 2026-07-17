# 21. Hermes Agent

Autonomer KI-Agent von [NousResearch](https://github.com/NousResearch/hermes-agent) (MIT-Lizenz), integriert als optionaler Stack-Service.

## Architektur

```
Teams / Web-Chat
      │
      ▼
hermes-gateway (Container)   ←→   Ollama (host.docker.internal:11434)
      │ shared volume
      ▼
hermes-dashboard (Container)
      │
      ▼
agent.brain.local (Caddy → forward_auth)
```

Zwei Services teilen sich ein Docker-Volume (`hermes_data`):

| Container | Funktion | Port |
|---|---|---|
| `hermes-gateway` | KI-Agent-Prozess + Teams-Gateway | intern |
| `hermes-dashboard` | Web-UI | 9119 (intern) |

## Starten

### Über das Dashboard (empfohlen)

Admin-Tab → Macro **„Hermes Agent starten"**

Das Macro startet `hermes-gateway` und `hermes-dashboard`. Beim ersten Start wird das Docker-Image automatisch gebaut (~5 Minuten, einmalig).

### Manuell

```bash
# Image einmalig bauen
docker compose build hermes-gateway

# Services starten
docker compose --profile optional up -d hermes-gateway hermes-dashboard

# Stoppen
docker compose stop hermes-dashboard hermes-gateway
```

### Autostart

`AUTOSTART_HERMES=true` (Standard in `.env.example`) startet `hermes-gateway` und `hermes-dashboard` automatisch mit dem Stack (`start_services.py`). Auf `false` setzen, um Hermes weiterhin manuell/über das Dashboard-Macro zu starten.

## Konfiguration

### `.env` – Pflichtfelder

```bash
HERMES_HOSTNAME=agent.brain.local
HERMES_UID=1000          # id -u
HERMES_GID=1000          # id -g
```

### `/etc/hosts` (lokal)

```bash
sudo sh -c 'echo "127.0.0.1 agent.brain.local" >> /etc/hosts'
```

### Modell anpassen

`hermes-config/cli-config.yaml` bearbeiten (im Repo, nicht im Volume):

```yaml
model:
  provider: "ollama"
  base_url: "http://host.docker.internal:11434/v1"
  default: "qwen2.5:7b"    # beliebiges lokales Ollama-Modell
```

Nach Änderungen: `docker compose restart hermes-gateway hermes-dashboard`

## Microsoft Teams Gateway

### Einmalige Azure-Registrierung

1. **Azure Portal → App registrations → New registration**
   - Name: `Hermes Agent` (beliebig)
   - Supported account types: *Single tenant*
   - Redirect URI: leer lassen
   - → **Application (client) ID** notieren → `TEAMS_CLIENT_ID`
   - → **Directory (tenant) ID** notieren → `TEAMS_TENANT_ID`

2. **Certificates & secrets → New client secret**
   - Beschreibung und Ablaufdatum wählen → **Value** notieren → `TEAMS_CLIENT_SECRET`

3. **Azure Bot Service erstellen** (Marketplace: „Azure Bot")
   - Bot handle: beliebig
   - Messaging endpoint: `https://<öffentliche-URL>:3978/api/messages`
   - App ID: die oben erstellte App-ID eintragen

4. **Channels → Microsoft Teams** aktivieren

5. **Eigene AAD Object-ID** ermitteln (Azure AD → Users → dein Account → Object ID)
   → in `TEAMS_ALLOWED_USERS` eintragen

### `.env` für Teams

```bash
TEAMS_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
TEAMS_CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TEAMS_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
TEAMS_ALLOWED_USERS=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
TEAMS_PORT=3978
```

### Öffentliche Erreichbarkeit

Teams sendet Webhooks an den Bot – der Stack muss von außen erreichbar sein:

```bash
# Lokale Entwicklung: Cloudflare Tunnel (kostenlos)
cloudflared tunnel --url http://localhost:3978

# Oder: Port 3978 in Caddy / Firewall freigeben (für Server-Betrieb)
```

Den Tunnel-URL als Messaging Endpoint im Azure Bot Service eintragen.

## Web-Dashboard ohne Teams

Das Web-Dashboard auf `https://agent.brain.local` funktioniert auch ohne Teams-Konfiguration. Leere `TEAMS_*`-Variablen deaktivieren den Teams-Gateway automatisch.

## Erreichbarkeit anderer Stack-Services

`hermes-gateway` läuft im selben Docker-Compose-Default-Netzwerk wie alle anderen Stack-Services und kann sie direkt über den Container-Namen erreichen, z. B.:

```
http://n8n:5678
http://qdrant:6333
http://neo4j:7474
http://searxng:8080
```

Für eine echte Tool-Anbindung (z. B. Hermes soll Qdrant/Neo4j abfragen oder Ergebnisse über den n8n-Webhook `kb-ingest-research` in die Wissensdatenbank schreiben, siehe [`docs/27_knowledge_base.md`](27_knowledge_base.md)) reicht Netzwerk-Erreichbarkeit allein nicht aus – Hermes bräuchte dafür einen MCP-Server, der diese Endpunkte als Tools bereitstellt (`mcp_servers:` in `hermes-config/cli-config.yaml`, siehe `hermes-agent/cli-config.yaml.example`). Ein solcher MCP-Server existiert im Stack aktuell nicht und ist bewusst nicht Teil dieser Integration – möglicher Folgeschritt.

## Submodul aktualisieren

```bash
cd hermes-agent
git fetch --depth 1 origin main
git checkout origin/main
cd ..
git add hermes-agent
git commit -m "chore: hermes-agent submodule update"
```
