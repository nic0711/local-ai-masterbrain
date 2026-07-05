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

## Rollen-Hierarchie

Drei Rollen, gesteuert über `.env`:

```bash
SUPERADMIN_EMAILS=owner@example.com           # Vollzugriff – auch User-Mgmt, Restore, Archiv
ADMIN_EMAILS=team1@example.com,team2@example.com  # Operativ – Service-Start/Stop, Backup, Macros
# alle anderen Supabase-User = "User" – nutzen Services (n8n, WebUI, Odysseus, …), keine Control-Endpoints
```

In `docker-compose.yml` werden beide Variablen automatisch an auth-gateway übergeben.

**Ohne Konfiguration:** Alle authentifizierten Nutzer haben Admin-Zugriff (Single-User-Betrieb). Für Team-Betrieb **müssen** beide Variablen gesetzt werden.

### Berechtigungen

| Endpoint | Superadmin | Admin | User |
|---|---|---|---|
| Alle Services nutzen (n8n, WebUI, Odysseus, …) | ✅ | ✅ | ✅ |
| Service start/stop/restart | ✅ | ✅ | ✗ |
| Macros ausführen | ✅ | ✅ | ✗ |
| Backup erstellen, Status, Liste | ✅ | ✅ | ✗ |
| Container-Logs lesen | ✅ | ✅ | ✗ |
| **Backup-Archiv-Inhalte lesen** | ✅ | ✗ | ✗ |
| **Datei-Diff anzeigen** | ✅ | ✗ | ✗ |
| **Restore auslösen** | ✅ | ✗ | ✗ |
| **User auflisten / anlegen** | ✅ | ✗ | ✗ |
| **Passwort zurücksetzen** | ✅ | ✗ | ✗ |
| **User löschen** | ✅ | ✗ | ✗ |

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

### Brute-Force-Schutz (Rate Limiting per IP)

| Endpoint | Limit |
|---|---|
| `GET /verify` | 600/min (parallel Asset-Loads erlaubt) |
| `GET /status` | 60/min |
| `GET/POST /control/backup/*` | 5–30/min je Endpoint |
| `GET/POST /control/users*` | 5–20/min je Endpoint |
| `POST /control/restore` | 3/min |
| `POST /control/services/{svc}/{action}` | 10/min |
| `GET /control/services/{svc}/logs` | 30/min |
| `POST /control/macro/{id}` | 5/min |

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
| `Max-Age` | 30 Tage (2592000s) | 30 Tage |
| `Domain` | `.brain.local` | `.yourdomain.com` |

**Hinweis:** Der Cookie selbst läuft nach 30 Tagen ab, der JWT darin nach 1h. Caddy verifiziert den JWT-Inhalt (inkl. `exp`-Claim) – ein abgelaufener JWT wird auch mit gültigem Cookie abgelehnt. Der 30-Tage-Cookie stellt sicher, dass der Browser das Cookie nicht löscht, bevor Auto-Refresh (`onAuthStateChange`) den JWT erneuert hat.

Der Cookie gilt für alle Subdomains (`*.brain.local` / `*.yourdomain.com`), nicht für externe Domains.

**Warum kein `HttpOnly`:** Das Supabase SDK muss das Token aus JavaScript lesen können, um es bei API-Calls weiterzuschicken. `HttpOnly`-Cookies wären für JS unsichtbar. Eine `HttpOnly`-Lösung würde eine server-seitige Session-Architektur erfordern (Caddy liest Cookie direkt, JS nutzt separate Cookie-Session).

---

## MFA / TOTP erzwingen (für Team-Server)

Standardmäßig ist MFA optional. Für den Team-Betrieb sollte MFA für alle Admins verpflichtend sein.

### Konfiguration in Supabase

```bash
# Supabase Dashboard → Authentication → Sign In / MFA
# → Enable MFA → "Required" für alle User
```

Alternativ via Supabase Management API:
```bash
curl -X PATCH "https://api.supabase.com/v1/projects/<project-ref>/auth/config" \
  -H "Authorization: Bearer <mgmt-token>" \
  -H "Content-Type: application/json" \
  -d '{"mfa_required": true}'
```

### Lokale Supabase-Instanz

In `supabase/docker/.env.local` (oder via Supabase Studio → Auth-Settings):
```bash
# GoTrue-Konfiguration
GOTRUE_MFA_ENABLED=true
```

### Was passiert bei aktiviertem MFA-Zwang?

1. User loggt sich mit Passwort ein
2. `mfa.getAuthenticatorAssuranceLevel()` gibt `aal.nextLevel = 'aal2'` zurück
3. Login-Flow zeigt automatisch TOTP-Eingabefeld (bereits implementiert in `auth.js`)
4. Ohne registrierten TOTP-Faktor: Login nicht möglich

### Backup bei verlorenem TOTP-Device

Superadmin kann TOTP-Faktor für einen User über die Supabase-Admin-API zurücksetzen:
```bash
# Alle MFA-Faktoren eines Users auflisten
SERVICE_KEY=$(grep "^SERVICE_ROLE_KEY=" .env | cut -d= -f2)
curl -s "http://localhost:8000/auth/v1/admin/users/<user-id>/factors" \
  -H "Authorization: Bearer $SERVICE_KEY" \
  -H "apikey: $SERVICE_KEY"

# Faktor löschen
curl -s -X DELETE "http://localhost:8000/auth/v1/admin/users/<user-id>/factors/<factor-id>" \
  -H "Authorization: Bearer $SERVICE_KEY" \
  -H "apikey: $SERVICE_KEY"
```

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
