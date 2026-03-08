# 1. Installation

## Voraussetzungen

- [Python 3](https://www.python.org/downloads/)
- [Git](https://git-scm.com/)
- [Docker Desktop](https://www.docker.com/products/docker-desktop) (Mac/Windows) oder Docker + Docker Compose v2 (Linux)

---

## Schritt 1: Repo klonen

```bash
git clone -b stable https://github.com/nic0711/local-ai-masterbrain
cd local-ai-masterbrain
```

## Schritt 2: `.env` anlegen und befüllen

```bash
cp .env.example .env
```

Alle Pflichtfelder mit eigenen Secrets befüllen – Anleitung in [02_configuration.md](02_configuration.md).

---

## Schritt 3: `/etc/hosts` (nur lokal)

Damit die Subdomains `brain.local`, `n8n.brain.local` etc. auflösen, einmalig eintragen:

```bash
sudo nano /etc/hosts
```

Folgende Zeilen hinzufügen:

```
127.0.0.1  brain.local
127.0.0.1  n8n.brain.local
127.0.0.1  webui.brain.local
127.0.0.1  flowise.brain.local
127.0.0.1  supabase.brain.local
127.0.0.1  langfuse.brain.local
127.0.0.1  neo4j.brain.local
127.0.0.1  crawl.brain.local
127.0.0.1  search.brain.local
127.0.0.1  qdrant.brain.local
127.0.0.1  minio.brain.local
```

> Auf dem Server entfällt dieser Schritt – DNS-A-Records übernehmen die Auflösung.

---

## Schritt 4: Stack starten

```bash
# Mac (Ollama lokal installiert, empfohlen)
python3 start_services.py --profile none

# Mac / CPU (Ollama in Docker)
python3 start_services.py --profile cpu

# Nvidia GPU
python3 start_services.py --profile gpu-nvidia

# AMD GPU (Linux)
python3 start_services.py --profile gpu-amd
```

Details zu allen Optionen: [03_start_services.md](03_start_services.md)

---

## Schritt 5: Browser-Zertifikat akzeptieren

Caddy stellt automatisch Self-Signed-Zertifikate aus. Beim ersten Besuch muss das Zertifikat akzeptiert werden:

1. `https://brain.local` → Zertifikat akzeptieren
2. `https://supabase.brain.local` → Zertifikat akzeptieren (wichtig für den Login!)
3. Weitere Subdomains beim ersten Besuch ebenfalls bestätigen

---

## Schritt 6: Ersten Benutzer anlegen

```bash
ANON_KEY=$(grep "^ANON_KEY=" .env | cut -d= -f2 | tr -d ' ')

curl -s -X POST "https://supabase.brain.local/auth/v1/signup" \
  -H "apikey: $ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{"email":"deine@email.de","password":"sicherespasswort"}'
```

Danach in der `.env` setzen und Stack neu starten:

```bash
DISABLE_SIGNUP=true
```

---

## Schritt 7: Login & optionale 2FA

1. `https://brain.local` im Browser öffnen
2. Email + Passwort eingeben
3. Optional: **„2FA einrichten"** → QR-Code mit Authenticator-App scannen → Code bestätigen

---

## Services & URLs (lokal)

| Service        | URL                              |
|----------------|----------------------------------|
| Dashboard      | https://brain.local              |
| n8n            | https://n8n.brain.local          |
| Open WebUI     | https://webui.brain.local        |
| Flowise        | https://flowise.brain.local      |
| Supabase       | https://supabase.brain.local     |
| Langfuse       | https://langfuse.brain.local     |
| Neo4j          | https://neo4j.brain.local        |
| Crawl4AI       | https://crawl.brain.local        |
| SearXNG        | https://search.brain.local       |
| Qdrant         | https://qdrant.brain.local       |
| Minio Console  | https://minio.brain.local        |
