# Anleitung & Tipps zur Supabase-Integration

## Schritt-für-Schritt-Anleitung: Supabase in bestehenden Stack integrieren

### 1. Supabase Docker Compose einbinden
- Supabase-Repo klonen (nur Docker-Ordner nötig):
  ```bash
  git clone --filter=blob:none --no-checkout https://github.com/supabase/supabase.git
  cd supabase
  git sparse-checkout init --cone
  git sparse-checkout set docker
  git checkout master
  cd ..
  ```
  *(Alternativ: Nur den Ordner `supabase/docker` in dein Projekt kopieren.)*

- In deiner Haupt-`docker-compose.yml` ganz oben einfügen:
  ```yaml
  include:
    - ./supabase/docker/docker-compose.yml
  ```
  *(Oder die Supabase-Services manuell in deine Compose-Datei übernehmen.)*

### 2. .env-Datei vorbereiten
- `.env` im Projekt-Root anlegen/ergänzen:
  ```env
  POSTGRES_PASSWORD=deinSicheresPasswort
  JWT_SECRET=deinJWTSecret
  ANON_KEY=deinSupabaseAnonKey
  SERVICE_ROLE_KEY=deinServiceRoleKey
  DASHBOARD_USERNAME=admin
  DASHBOARD_PASSWORD=deinDashboardPasswort
  POOLER_TENANT_ID=irgendeinWert
  ```
  *(Weitere Variablen für Caddy, n8n, Langfuse etc. ergänzen.)*

### 3. Supabase-Ports & Netzwerk prüfen
- Standardmäßig läuft Supabase auf Port 8000 (API Gateway/Kong).
- Stelle sicher, dass Port 8000 nicht von anderen Diensten belegt ist.
- Optional: Passe Ports in `supabase/docker/docker-compose.yml` an, falls nötig.

### 4. Caddy Reverse Proxy konfigurieren
- In deiner `Caddyfile` hinzufügen:
  ```caddyfile
  supabase.deinedomain.tld {
      reverse_proxy localhost:8000
  }
  ```
  *(Oder nutze die Variable wie im Beispiel: `{$SUPABASE_HOSTNAME}`)*
- Umgebungsvariable für Caddy setzen (in `.env`):
  ```env
  SUPABASE_HOSTNAME=supabase.deinedomain.tld
  ```

### 5. Supabase starten
- Mit Docker Compose starten:
  ```bash
  docker compose up -d
  ```
  *(Oder: `docker compose -f supabase/docker/docker-compose.yml up -d` falls separat.)*
- Logs prüfen:
  ```bash
  docker compose logs -f kong
  docker compose logs -f db
  ```

### 6. Supabase Studio & API testen
- Studio öffnen: http://localhost:8000 (bzw. deine Domain/Subdomain)
- Mit Dashboard-User einloggen (siehe `.env`).
- API-Keys in Supabase Studio kopieren, falls du sie für n8n brauchst.

### 7. n8n/Backend anbinden
- In n8n neue Credentials für Supabase anlegen:
  - Host: `db` (so heißt der Service im Compose-Netzwerk)
  - User: `postgres`
  - Passwort: wie in `.env`
  - DB: `postgres`
  - Für Vector Store: Supabase-API-URL und Key aus Studio verwenden
- Workflows anpassen:
  - Nutze die Supabase-Nodes für Datenbank- und Vektor-Operationen.
  - Beispiel: `@n8n/n8n-nodes-langchain.vectorStoreSupabase`

### 8. (Optional) Backup & Persistenz
- Volumes für Supabase-Datenbank und Storage prüfen/definieren (in Compose).
- Regelmäßige Backups einrichten (z.B. per pg_dump oder Supabase-Tools).

### 9. (Optional) Sicherheit & Produktion
- Starke Passwörter und Secrets verwenden!
- Caddy TLS/HTTPS aktivieren (Let's Encrypt).
- Firewall/Netzwerkzugriffe absichern.
- Supabase-Admin-Panel ggf. nur intern zugänglich machen.

---

# Tipps & Troubleshooting für Supabase-Integration

## Supabase Troubleshooting

### 1. Supabase Pooler Container startet ständig neu
- **Lösung:** Folge den Anweisungen in diesem [GitHub-Issue](https://github.com/supabase/supabase/issues/30210#issuecomment-2456955578).

### 2. Supabase Analytics startet nach Passwort-Änderung nicht mehr
- **Lösung:** Lösche den Ordner `supabase/docker/volumes/db/data` und starte die Container neu. Dadurch wird die Datenbank neu initialisiert (Achtung: Datenverlust möglich!).

### 3. Supabase Service nicht erreichbar
- **Lösung:**
  - Stelle sicher, dass **kein "@"-Zeichen** im Postgres-Passwort verwendet wird. Das führt zu Problemen mit der Verbindung.
  - Prüfe, ob andere Sonderzeichen im Passwort ebenfalls Probleme verursachen.
  - Prüfe die Logs des Kong-Containers (`docker compose logs -f kong`).
  - Prüfe, ob der Port 8000 frei ist und nicht von anderen Diensten belegt wird.

### 4. Docker Desktop: Daemon nicht erreichbar
- **Lösung:** In den Docker-Einstellungen "Expose daemon on tcp://localhost:2375 without TLS" aktivieren.

### 5. Verbindung von n8n zu Supabase/Postgres schlägt fehl
- **Lösung:**
  - Hostname in n8n-Credentials muss `db` sein (so heißt der Service im Compose-Netzwerk).
  - User: `postgres`, Passwort und DB wie in `.env`.
  - Prüfe, ob die Supabase-Container laufen (`docker compose ps`).

### 6. Supabase Studio Login schlägt fehl
- **Lösung:**
  - Nutze die in `.env` hinterlegten Dashboard-Userdaten.
  - Prüfe, ob die Studio-URL korrekt ist (meist http://localhost:8000 oder deine Subdomain).

### 7. Caddy Reverse Proxy funktioniert nicht
- **Lösung:**
  - Prüfe, ob die Umgebungsvariable `SUPABASE_HOSTNAME` korrekt gesetzt ist.
  - Prüfe die Caddyfile auf Tippfehler.
  - Prüfe, ob Caddy neu gestartet wurde nach Änderungen.

### 8. Datenpersistenz/Backups
- **Tipp:**
  - Stelle sicher, dass die Volumes für Supabase/Postgres korrekt gemountet sind.
  - Richte regelmäßige Backups ein (z.B. mit `pg_dump`).

### 9. Sicherheit
- **Tipp:**
  - Verwende starke, zufällige Passwörter und Secrets.
  - Setze Supabase Studio und Admin-Panel nur intern oder mit Authentifizierung aus.
  - Aktiviere HTTPS in Caddy für alle externen Dienste.

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

**Weitere Hilfe:**
- [Supabase Self-Hosting Guide](https://supabase.com/docs/guides/self-hosting/docker)
- [Supabase GitHub Issues](https://github.com/supabase/supabase/issues)
- [n8n Community](https://community.n8n.io/)
- [Caddy Doku](https://caddyserver.com/docs/) 