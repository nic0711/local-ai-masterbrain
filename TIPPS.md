# Konfiguration & Wichtige Hinweise

Dieser Stack ist so vorkonfiguriert, dass die Dienste nahtlos zusammenarbeiten. Hier sind die wichtigsten Punkte, die du für Anpassungen oder zum Debugging kennen solltest.

### 1. Caddy als zentraler Reverse Proxy
- **Alle Anfragen** von außen (z.B. `http://localhost:8001` oder `https://n8n.deinedomain.de`) laufen über den **Caddy-Container**.
- Caddy leitet die Anfragen an die internen Docker-Services weiter.
- Die Hostnamen (lokal die Ports, public die Domains) werden zentral über die `.env`-Datei und die `environment`-Sektion des Caddy-Services in der `docker-compose.yml` gesteuert.

### 2. n8n-Anbindung an die Supabase-Datenbank
- Um n8n mit der Postgres-Datenbank von Supabase zu verbinden, nutze folgende Einstellungen in den n8n-Credentials:
  - **Host**: `db` (Dies ist der interne Service-Name des Postgres-Containers im Docker-Netzwerk).
  - **User**: `postgres`
  - **Passwort**: Das `POSTGRES_PASSWORD` aus deiner `.env`-Datei.
  - **Datenbank**: `postgres`

### 3. Dashboard-Konfiguration
- Die Links auf dem Dashboard werden dynamisch über die Datei `dashboard/config.js` gesteuert.
- Für die **lokale Entwicklung** ist eine statische `config.js` mit `localhost`-Links ausreichend.
- Für das **Public-Deployment** muss diese Datei angepasst werden, um die öffentlichen Domains zu verwenden und die Authentifizierung zu aktivieren. Siehe Anleitung unten.

---

# Tipps & Troubleshooting

## Supabase Troubleshooting

### 1. Supabase Pooler Container startet ständig neu
- **Lösung:** Folge den Anweisungen in diesem GitHub-Issue.

### 2. Supabase-Container (z.B. Analytics) startet nach Passwort-Änderung nicht mehr
- **Lösung:** Lösche den Ordner `supabase/docker/volumes/db/data` und starte die Container neu. Dadurch wird die Datenbank neu initialisiert (**Achtung: Datenverlust der Postgres-DB!**).

### 3. Supabase Service nicht erreichbar
- **Lösung:**
  - Stelle sicher, dass **kein "@"-Zeichen** im `POSTGRES_PASSWORD` verwendet wird. Das führt zu Verbindungsproblemen.
  - Prüfe die Logs des Kong-Containers (`docker compose logs -f kong`).

### 4. Supabase Studio Login schlägt fehl
- **Lösung:**
  - Der Login für das Supabase Studio (erreichbar über den Dashboard-Link) verwendet **nicht** die `DASHBOARD_USERNAME`/`PASSWORD` aus älteren `.env`-Versionen. Der Standard-Login ist `supabase@example.com` mit dem Passwort `this-is-a-safe-password`. Dies sollte für den Produktivbetrieb unbedingt geändert werden.

---

## Allgemeine Tipps für den Stack

- **Container-Logs prüfen:**
  ```bash
  docker compose logs -f <servicename>
  ```
- **Container-Status prüfen:**
  ```bash
  docker compose ps
  ```
- **Umgebungsvariablen:**
  - Prüfe `.env` auf Tippfehler und fehlende Werte.
- **Netzwerk:**
  - Alle Services müssen im selben Docker-Netzwerk laufen (Compose regelt das automatisch).
- **Updates:**
  - Container werden nicht automatisch aktualisiert. Nutze `docker compose pull` und dann `docker compose up -d` für Updates.

---

# Anleitung: Deployment auf einem öffentlichen Server (VPS)

Diese Anleitung beschreibt, wie du den gesamten Stack von der lokalen Entwicklungsumgebung auf einen öffentlichen Server (VPS) für den produktiven Einsatz umziehst. Die Architektur ist darauf ausgelegt, diesen Wechsel so einfach wie möglich zu gestalten.

## Voraussetzungen

1.  Ein VPS mit einem Linux-Betriebssystem (z.B. Ubuntu 22.04).
2.  Docker und Docker Compose sind auf dem VPS installiert.
3.  Eine Domain (z.B. `deinedomain.de`) und die Möglichkeit, DNS-Einträge zu verwalten.

## Schritt 1: DNS Konfigurieren

Leite alle Subdomains, die du verwenden möchtest, per **A-Record** auf die öffentliche IP-Adresse deines VPS.

**Beispiel-DNS-Einträge:**
- `dashboard.deinedomain.de` -> `A` -> `DEINE_VPS_IP`
- `n8n.deinedomain.de` -> `A` -> `DEINE_VPS_IP`
- `webui.deinedomain.de` -> `A` -> `DEINE_VPS_IP`
- `supabase.deinedomain.de` -> `A` -> `DEINE_VPS_IP`
- ... und so weiter für alle Dienste.

## Schritt 2: Projekt auf den Server kopieren

Klone oder kopiere das gesamte Projektverzeichnis auf deinen VPS.

```bash
git clone https://github.com/dein-repo/local-ai-packaged.git
cd local-ai-packaged
```

## Schritt 3: `.env`-Datei für die Produktion anpassen

Erstelle im Hauptverzeichnis des Projekts eine `.env`-Datei. Hier werden alle Umgebungsvariablen zentral verwaltet. Dies ist der **einzige Ort**, den du für den Wechsel von lokal zu public anpassen musst.

**Beispiel `.env` für den Public-Betrieb:**
```env
# --- Caddy Hostnames ---
# Ersetze die Beispiel-Domains durch deine eigenen.
DASHBOARD_HOSTNAME=dashboard.deinedomain.de
N8N_HOSTNAME=n8n.deinedomain.de
WEBUI_HOSTNAME=webui.deinedomain.de
FLOWISE_HOSTNAME=flowise.deinedomain.de
SUPABASE_HOSTNAME=supabase.deinedomain.de
SEARXNG_HOSTNAME=search.deinedomain.de
LANGFUSE_HOSTNAME=langfuse.deinedomain.de
NEO4J_HOSTNAME=neo4j.deinedomain.de
CRAWL4AI_HOSTNAME=crawl.deinedomain.de
QDRANT_HOSTNAME=qdrant.deinedomain.de
MINIO_HOSTNAME=minio.deinedomain.de
PYTHON_NLP_HOSTNAME=nlp-api.deinedomain.de

# --- Caddy SSL ---
# Wichtig, damit Caddy gültige SSL-Zertifikate von Let's Encrypt erhält.
LETSENCRYPT_EMAIL=deine-echte-email@deinedomain.de

# --- Supabase & Auth ---
# Starke, zufällige Passwörter und Secrets verwenden!
POSTGRES_PASSWORD=DEIN_STARKES_POSTGRES_PASSWORT
JWT_SECRET=DEIN_SEHR_LANGES_UND_SICHERES_JWT_SECRET
ANON_KEY=DEIN_SUPABASE_ANON_KEY_HIER_EINFUEGEN
SERVICE_ROLE_KEY=DEIN_SUPABASE_SERVICE_ROLE_KEY_HIER_EINFUEGEN
```

## Schritt 4: Dashboard-Konfiguration anpassen

Die Datei `dashboard/config.js` muss für den Produktivbetrieb angepasst werden, damit die Links auf die öffentlichen Domains zeigen und die Authentifizierung aktiviert wird.

**Ersetze den Inhalt von `dashboard/config.js` mit folgendem Code:**

```javascript
// dashboard/config.js für den Public-Betrieb
window.APP_CONFIG = {
  // --- Authentifizierung ---
  // Für den Public-Betrieb auf `true` setzen, um die Login-Seite zu aktivieren.
  authEnabled: true,

  // --- Supabase-Konfiguration ---
  // Ersetze die Werte durch deine öffentlichen Domains und Keys aus der .env-Datei.
  supabaseUrl: "https://supabase.deinedomain.de",
  supabaseAnonKey: "DEIN_SUPABASE_ANON_KEY_HIER_EINFUEGEN",

  // --- Service Hostnamen für die Links ---
  // Ersetze die Domains durch deine eigenen.
  n8nHostname: "https://n8n.deinedomain.de",
  openWebuiHostname: "https://webui.deinedomain.de",
  searxngHostname: "https://search.deinedomain.de",
  flowiseHostname: "https://flowise.deinedomain.de",
  supabaseHostname: "https://supabase.deinedomain.de", // Link zum Supabase Studio
  langfuseHostname: "https://langfuse.deinedomain.de",
  neo4jHostname: "https://neo4j.deinedomain.de",
  qdrantHostname: "https://qdrant.deinedomain.de",
  minioHostname: "https://minio.deinedomain.de",
  crawl4aiHostname: "https://crawl.deinedomain.de",
  pythonNlpHostname: "https://nlp-api.deinedomain.de/status", // Link zum Status-Endpunkt
};
```

## Schritt 5: Firewall konfigurieren

Stelle sicher, dass die Firewall deines VPS die Ports für Web-Traffic zulässt:
```bash
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable
```

## Schritt 6: Stack starten

Starte alle Container. Da wir nun eine `.env`-Datei mit Hostnamen haben, wird Caddy automatisch versuchen, SSL-Zertifikate für diese zu beziehen. Der `public`-Profil wird ebenfalls aktiviert, was den `auth-gateway` startet.

```bash
docker compose --profile public up -d
```

Dein Dashboard sollte nun unter `https://dashboard.deinedomain.de` erreichbar sein und die Login-Seite anzeigen. Alle anderen Dienste sind ebenfalls über ihre jeweiligen Subdomains erreichbar.

