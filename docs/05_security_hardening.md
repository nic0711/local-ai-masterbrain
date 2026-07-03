# 5. Security Hardening

## Authentifizierungs-Architektur

Alle Services (n8n, Open WebUI, Flowise, etc.) sind durch Caddy's `forward_auth` geschützt.

**Flow:**
1. Browser ruft `https://brain.local` auf → Login mit Email + Passwort (+ TOTP falls aktiviert)
2. Nach Login setzt das Dashboard einen `sb-access-token` Cookie auf `.brain.local`
3. Zugriff auf `https://n8n.brain.local` → Caddy liest Cookie → sendet `Authorization: Bearer <token>` an `auth-gateway:5001/verify`
4. Gültig → Zugriff erlaubt; ungültig → Redirect zu `https://brain.local/login.html`

**Warum Cookie statt localStorage:**
Caddy's `forward_auth` hat nur Zugriff auf Request-Headers und Cookies – nicht auf localStorage. Der Cookie wird nach Login gesetzt und bei jedem Token-Refresh via `onAuthStateChange` aktualisiert.

---

## 2FA / TOTP

TOTP ist über Supabase GoTrue nativ eingebaut und wird im `public`-Environment automatisch aktiviert.

### Ersteinrichtung (pro Benutzer)

1. Login mit Email + Passwort
2. **„2FA einrichten"** im Dashboard-Header klicken
3. QR-Code mit Google Authenticator, Authy oder ähnlicher App scannen
4. 6-stelligen Code eingeben → bestätigen

### Login mit aktivierter 2FA

1. Email + Passwort eingeben
2. TOTP-Eingabefeld erscheint automatisch
3. Code aus Authenticator-App eingeben → Zugang

### Token-Refresh

Das Supabase SDK erneuert JWTs automatisch vor Ablauf. `onAuthStateChange` in `auth.js` aktualisiert dabei den Cookie, sodass die Session nahtlos weiterläuft.

---

## Benutzer verwalten

### Passwort zurücksetzen

```bash
USER_ID=$(docker exec supabase-db psql -U postgres -d postgres -tAc \
  "SELECT id FROM auth.users WHERE email='user@example.com';" | tr -d ' ')
SERVICE_KEY=$(grep "^SERVICE_ROLE_KEY=" .env | cut -d= -f2 | tr -d ' ')

curl -s -X PUT "http://localhost:8000/auth/v1/admin/users/$USER_ID" \
  -H "apikey: $SERVICE_KEY" \
  -H "Authorization: Bearer $SERVICE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"password":"neuespasswort"}'
```

### Alle Benutzer anzeigen

```bash
docker exec supabase-db psql -U postgres -d postgres \
  -c "SELECT email, created_at, last_sign_in_at FROM auth.users;"
```

### Signup deaktivieren (nach erstem User)

In `.env`:
```bash
DISABLE_SIGNUP=true
```
Stack neu starten.

---

## Server-Härtung

### Als Non-root ausführen

```bash
sudo adduser --system --group --home /opt/appservice appservice
sudo usermod -aG docker appservice
sudo -u appservice python3 start_services.py --profile cpu
```

### SSH absichern

```bash
sudo sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo sed -i 's/#PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sudo systemctl restart sshd
```

### Fail2ban & automatische Updates

```bash
sudo apt install fail2ban unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

### Firewall (UFW + Docker-Fix)

```bash
sudo ufw enable
sudo ufw allow 22
sudo ufw allow 80
sudo ufw allow 443

# Docker umgeht UFW – dieser Fix verhindert direkten Port-Zugriff:
sudo iptables -I DOCKER-USER -i eth0 ! -s 192.168.0.0/16 -j DROP
sudo apt install iptables-persistent
```

---

## Admin-Rollenkontrolle

Privilegierte Control-Endpoints (User-Management, Service-Start/Stop, Macros, Backup, Restore) erfordern zusätzlich zur JWT-Authentifizierung Admin-Rechte.

### Konfiguration

In `.env`:
```bash
# Kommagetrennte E-Mail-Adressen mit Admin-Zugriff
ADMIN_EMAILS=you@example.com,admin2@example.com
```

In `docker-compose.yml` wird `ADMIN_EMAILS` automatisch an auth-gateway übergeben.

**Ohne `ADMIN_EMAILS`** (leere Variable): Alle authentifizierten Nutzer haben Admin-Zugriff. Das ist für lokale Single-User-Setups (`brain.local`) akzeptabel. Für externe Server **muss** `ADMIN_EMAILS` gesetzt sein.

Beim Start loggt auth-gateway eine Warnung wenn `ADMIN_EMAILS` nicht konfiguriert ist:
```
WARNING: ADMIN_EMAILS nicht gesetzt – alle auth. Nutzer haben Admin-Zugriff...
```

### Betroffene Endpoints (Auth + Admin)

| Endpoint | Funktion |
|---|---|
| `POST /control/backup` | Backup erstellen |
| `GET /control/backup/files` | Archiv-Inhalte lesen |
| `GET /control/backup/diff` | Datei-Diff anzeigen |
| `POST /control/restore` | Restore auslösen |
| `GET/POST /control/users` | Benutzer auflisten / anlegen |
| `POST /control/users/password` | Passwort zurücksetzen |
| `POST /control/users/delete` | Benutzer löschen |
| `POST /control/services/{svc}/{action}` | Service starten/stoppen/neustarten |
| `GET /control/services/{svc}/logs` | Container-Logs lesen |
| `POST /control/macro/{id}` | Macro ausführen |

Nur-Lese-Endpoints (`/control/backup/status`, `/control/backup/list`, `/control/services/status`, `/control/macros`) sind für alle authentifizierten Nutzer zugänglich.

---

## Auth-Gateway Performance

### JWT-Verifikation

Der auth-gateway verifiziert JWTs **lokal** via PyJWT – ohne HTTP-Call zu Supabase.

```
Browser → Caddy → forward_auth → auth-gateway /verify
                                   → PyJWT.decode(token, JWT_SECRET)  # <1ms, kein Netzwerk
                                   → Cache-Lookup (5min TTL)
```

**Warum lokal statt Supabase-API:**
Caddy ruft `/verify` für **jeden** Asset-Request auf (HTML, JS, CSS, Fonts...). Ein großes Frontend (Langfuse, Supabase Studio) lädt 50–150 Assets – das wären 50–150 Supabase-HTTP-Calls (~30ms each = mehrere Sekunden Wartezeit).

Mit lokaler Verifikation: <1ms pro Check, alle Assets laden parallel.

**Tradeoff:** Manuell gesperrte Sessions werden erst beim Token-Ablauf (max. 1h) erkannt.
Für den üblichen Anwendungsfall (Logout via Dashboard) kein Problem – der Cookie wird dabei gelöscht.

### Konfiguration

```yaml
# docker-compose.yml – auth-gateway
environment:
  - JWT_SECRET=${JWT_SECRET}      # Supabase JWT Secret aus .env
  - ADMIN_EMAILS=${ADMIN_EMAILS:-} # Kommaliste Admin-E-Mails (leer = alle)
```

### JWT Audience-Verifikation

auth-gateway prüft bei lokaler JWT-Verifikation die `aud`-Claim auf `"authenticated"`. Das verhindert, dass Tokens mit anderen Audiences (z.B. Service-Role-Tokens) für normale User-Auth verwendet werden.

### Brute-Force-Schutz

`/verify` ist auf **600 Req/min** begrenzt (Flask-Limiter, pro IP).
Das erlaubt normale Browser-Nutzung (parallel Asset-Loads), blockiert aber Scripting-Angriffe.

### Concurrency

```
gunicorn: 1 Worker + 16 gThreads
```
Ein Prozess = geteilter JWT-Cache. Mit mehreren Prozessen hätte jeder seinen eigenen Cache → Cache-Misses bei selten genutzten Services.

---

## Cookie-Sicherheit

| Eigenschaft | Lokal (`.local`) | Produktion |
|---|---|---|
| `Secure` | Nein (Self-Signed blockiert es) | Ja |
| `SameSite` | Lax | Lax |
| `HttpOnly` | Nein (JS muss den Cookie setzen) | Nein |
| `Max-Age` | 3600s (1h) | 3600s (1h) |
| `Domain` | `.brain.local` | `.yourdomain.com` |

Der Cookie gilt für alle Subdomains (`*.brain.local` / `*.yourdomain.com`), nicht für externe Domains.

**Warum kein `HttpOnly`:** Das Supabase SDK muss das Token aus JavaScript lesen können, um es bei API-Calls weiterzuschicken. `HttpOnly`-Cookies wären für JS unsichtbar. Eine `HttpOnly`-Lösung würde eine server-seitige Session-Architektur erfordern (Caddy liest Cookie direkt, JS nutzt separate Cookie-Session).

---

## Content Security Policy (Dashboard)

Das Dashboard (`brain.local`) sendet einen strikten CSP-Header:

```
Content-Security-Policy:
  default-src 'self';
  script-src 'self' https://cdn.jsdelivr.net;   # Supabase JS (mit SRI)
  style-src 'self' 'unsafe-inline';
  img-src 'self' data: blob:;                   # QR-Codes für 2FA-Enrollment
  font-src 'self';
  connect-src 'self' https://{SUPABASE_HOSTNAME}; # Supabase Auth API
  frame-ancestors 'none'                         # kein iFrame-Embedding
```

Andere Services (n8n, Grafana, Langfuse) senden ihre eigenen CSP-Header – kein globaler Override durch Caddy.

---

## Bekannte Einschränkungen

| Thema | Status | Begründung |
|---|---|---|
| Cookie ohne `HttpOnly` | Bewusst | JS muss Token lesen (Supabase SDK) |
| AnonKey im Frontend | Akzeptiert | Supabase-Design-Muster; durch RLS + `DISABLE_SIGNUP=true` geschützt |
| Docker-Socket-Zugriff in auth-gateway | Notwendig | Pflicht für Service Control (start/stop) |
| `SERVICE_ROLE_KEY` in Env-Vars | Standard | Docker-Pattern; kein Fix ohne Swarm Secrets |
