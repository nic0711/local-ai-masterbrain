# 4. Cloud Deployment

## Voraussetzungen

- Linux VPS (Ubuntu empfohlen)
- Docker + Docker Compose v2 installiert
- DNS A-Records für alle Subdomains zeigen auf die Server-IP

---

## Schritt 1: Docker Compose v2 installieren (falls nicht vorhanden)

```bash
DOCKER_COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep 'tag_name' | cut -d\" -f4)
sudo curl -L "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-linux-x86_64" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
sudo mkdir -p /usr/local/lib/docker/cli-plugins
sudo ln -s /usr/local/bin/docker-compose /usr/local/lib/docker/cli-plugins/docker-compose
```

## Schritt 2: Firewall (UFW)

```bash
sudo ufw enable
sudo ufw allow 22    # SSH
sudo ufw allow 80    # HTTP (Caddy → HTTPS Redirect)
sudo ufw allow 443   # HTTPS
sudo ufw reload
```

> ⚠️ Docker bypasses UFW by default. To prevent containers from exposing ports directly:
> ```bash
> sudo iptables -I DOCKER-USER -i eth0 ! -s 192.168.0.0/16 -j DROP
> sudo apt install iptables-persistent
> ```
> With `--environment public` (the default), all service ports except 80/443 are already closed by Docker Compose.

## Schritt 3: Repo klonen & `.env` befüllen

```bash
git clone -b stable https://github.com/nic0711/local-ai-masterbrain
cd local-ai-masterbrain
cp .env.example .env
nano .env   # Secrets & Produktions-Domain eintragen
```

In der `.env` den Produktions-Block aktivieren (Kommentarzeichen entfernen) und lokalen Block auskommentieren.

## Schritt 4: Stack starten

```bash
# Nvidia GPU
python3 start_services.py --profile gpu-nvidia

# CPU only
python3 start_services.py --profile cpu

# Ollama extern / nicht in Docker
python3 start_services.py --profile none
```

`--environment public` ist der Standard und muss nicht angegeben werden. Caddy holt automatisch Let's Encrypt-Zertifikate für alle konfigurierten Domains.

## Schritt 5: DNS-Records setzen

Für jede Subdomain einen A-Record anlegen, der auf die Server-IP zeigt:

| Hostname | Typ | Wert |
|---|---|---|
| `brain.yourdomain.com` | A | `<Server-IP>` |
| `n8n.yourdomain.com` | A | `<Server-IP>` |
| `webui.yourdomain.com` | A | `<Server-IP>` |
| `flowise.yourdomain.com` | A | `<Server-IP>` |
| `supabase.yourdomain.com` | A | `<Server-IP>` |
| `langfuse.yourdomain.com` | A | `<Server-IP>` |
| `neo4j.yourdomain.com` | A | `<Server-IP>` |
| `crawl.yourdomain.com` | A | `<Server-IP>` |
| `search.yourdomain.com` | A | `<Server-IP>` |
| `qdrant.yourdomain.com` | A | `<Server-IP>` |
| `minio.yourdomain.com` | A | `<Server-IP>` |

## Schritt 6: Ersten Benutzer anlegen

```bash
ANON_KEY=$(grep "^ANON_KEY=" .env | cut -d= -f2 | tr -d ' ')

curl -s -X POST "https://supabase.yourdomain.com/auth/v1/signup" \
  -H "apikey: $ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@yourdomain.com","password":"sicherespasswort"}'
```

Danach `DISABLE_SIGNUP=true` in der `.env` setzen und Stack neu starten.

## Weiterführend

- Security Hardening: [05_security_hardening.md](05_security_hardening.md)
- Backup-Strategie: [08_backup_and_recovery.md](08_backup_and_recovery.md)
