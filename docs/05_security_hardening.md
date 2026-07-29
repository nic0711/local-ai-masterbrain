# 5. Security Hardening

## Authentifizierungs-Architektur

Alle Services (n8n, Open WebUI, Flowise, etc.) sind durch Caddy's `forward_auth` geschützt.

**Flow:**
1. Browser ruft `https://brain.local` auf → Login mit Email + Passwort, danach TOTP-Schritt (siehe [2FA / TOTP](#2fa--totp) – standardmäßig erzwungen)
2. Nach vollständigem Login (inkl. TOTP) sendet `dashboard/auth.js` das Token per `POST /_auth/session` an den auth-gateway. Dieser verifiziert es (inkl. `aal2`-Pflicht) und setzt den `sb-access-token` Cookie selbst per `Set-Cookie` – `HttpOnly`, `Secure`, `SameSite=Lax` (siehe [Cookie-Sicherheit](#cookie-sicherheit)). `supabase-js` behält seine eigene Session unabhängig davon in `localStorage`.
3. Zugriff auf `https://n8n.brain.local` → Caddy liest Cookie → sendet `Authorization: Bearer <token>` an `auth-gateway:5001/verify`
4. `/verify` prüft Signatur, `exp`, `aud` **und den `aal`-Claim** (Multi-Factor-Level). Nur `aal2` (Passwort **und** TOTP abgeschlossen) → Zugriff erlaubt; `aal1` (nur Passwort) oder ungültig → Redirect zu `https://brain.local/login.html`

**Wichtig:** Die TOTP-Prüfung passiert nicht nur im Login-Formular, sondern wird vom auth-gateway bei **jedem** `/verify`-Call serverseitig durchgesetzt. Ein Token, das GoTrue nach reinem Passwort-Login ausstellt, trägt `aal: "aal1"` und wird sowohl von `/session` (401, kein Cookie wird gesetzt) als auch von `/verify` (401 MFA required) abgelehnt. Abschaltbar über `MFA_REQUIRED=false` in `.env` (Notfall-Kill-Switch, siehe [MFA / TOTP erzwingen](#mfa--totp-erzwingen-team-server)).

**Warum Cookie statt localStorage:**
Caddy's `forward_auth` hat nur Zugriff auf Request-Headers und Cookies – nicht auf localStorage. Der Cookie wird nach Login gesetzt und bei jedem Token-Refresh via `onAuthStateChange` über denselben `POST /_auth/session`-Roundtrip aktualisiert – `dashboard/auth.js` liest oder schreibt den Cookie-Wert nie direkt.

---

## 2FA / TOTP

TOTP ist über Supabase GoTrue nativ eingebaut. **Seit `MFA_REQUIRED=true` (Default) ist 2FA für alle Nutzer verpflichtend** – der auth-gateway lässt ohne abgeschlossenen TOTP-Schritt (`aal2`) keinen Zugriff auf geschützte Dienste zu (siehe [Authentifizierungs-Architektur](#authentifizierungs-architektur)). Nutzer ohne eingerichteten Faktor werden nach dem Login automatisch zum Profil-Tab mit Einrichtungs-Hinweis geleitet; das Dashboard selbst bleibt dafür ohne `forward_auth` erreichbar (kein Lockout-Risiko).

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
# alle anderen Supabase-User = "User" – nutzen Services (n8n, WebUI, Hermes, …), keine Control-Endpoints
```

In `docker-compose.yml` werden beide Variablen automatisch an auth-gateway übergeben.

**Fail-closed:** Ohne Konfiguration hat **niemand** Admin- oder Superadmin-Zugriff (`_require_admin`/`_require_superadmin` geben `False` zurück, wenn keine E-Mails hinterlegt sind). Für Team- **und** Single-User-Betrieb **muss** mindestens `SUPERADMIN_EMAILS` gesetzt sein, sonst sind alle Control-Endpoints außer den reinen Status-Abfragen für niemanden erreichbar.

**MFA-Voraussetzung:** Admin- und Superadmin-Rechte erfordern zusätzlich `aal2` (abgeschlossene 2FA) – ein reines Passwort-Token wird von `_require_admin`/`_require_superadmin` unabhängig von der E-Mail-Liste abgelehnt.

### Berechtigungen

| Endpoint | Superadmin | Admin | User |
|---|---|---|---|
| Alle Services nutzen (n8n, WebUI, Hermes, …) | ✅ | ✅ | ✅ |
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
| **2FA eines Users zurücksetzen** | ✅ | ✗ | ✗ |

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
| `POST /control/users/mfa-reset` | 10/min |
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
| `Secure` | Ja (immer gesetzt bei `https:`, unabhängig von `.local`) | Ja |
| `SameSite` | Lax | Lax |
| `HttpOnly` | Ja | Ja |
| `Max-Age` | 30 Tage (2592000s) | 30 Tage |
| `Domain` | `.brain.local` | `.yourdomain.com` |

**Hinweis:** Der Cookie selbst läuft nach 30 Tagen ab, der JWT darin nach 1h. Caddy verifiziert den JWT-Inhalt (inkl. `exp`-Claim) – ein abgelaufener JWT wird auch mit gültigem Cookie abgelehnt. Der 30-Tage-Cookie stellt sicher, dass der Browser das Cookie nicht löscht, bevor Auto-Refresh (`onAuthStateChange`) den JWT erneuert hat.

Der Cookie gilt für alle Subdomains (`*.brain.local` / `*.yourdomain.com`), nicht für externe Domains.

**Wie das `HttpOnly`-Cookie funktioniert:** Früher setzte `dashboard/auth.js` den Cookie direkt per `document.cookie` – damit war er für jedes im Dashboard laufende JavaScript lesbar, eine XSS-Lücke hätte den Token direkt stehlen können. Jetzt läuft das Setzen/Löschen über den auth-gateway:

- `POST /_auth/session` (Body: `{"access_token": "<jwt>"}`) – verifiziert das Token (inkl. `aal2`-Pflicht) und setzt den Cookie per `Set-Cookie` mit `HttpOnly`.
- `POST /_auth/session/logout` – löscht den Cookie serverseitig.

`supabase-js` liest/schreibt seine eigene Session weiterhin unverändert in `localStorage` – das Cookie ist ausschließlich der Träger für Caddys `forward_auth` und für clientseitiges JavaScript nicht mehr einsehbar. Endpoint-Details siehe [15_api_reference.md](15_api_reference.md).

---

## MFA / TOTP erzwingen (Team-Server)

**MFA ist standardmäßig erzwungen** (`MFA_REQUIRED=true`) – nicht über eine Supabase/GoTrue-Einstellung, sondern durch den auth-gateway selbst: `/verify` prüft bei jedem Request den `aal`-Claim des JWTs und lehnt `aal1`-Tokens (nur Passwort, TOTP nicht abgeschlossen) mit `401 MFA required` ab. Das ist robuster als eine reine GoTrue-Konfiguration, weil es unabhängig davon greift, wie das Token ausgestellt wurde.

### Was passiert im Detail?

1. User loggt sich mit Passwort ein → GoTrue stellt ein `aal1`-Token aus
2. `dashboard/auth.js` prüft `mfa.getAuthenticatorAssuranceLevel()`:
   - Faktor vorhanden, `nextLevel = 'aal2'` → TOTP-Eingabefeld erscheint automatisch, Cookie wird erst nach erfolgreicher TOTP-Verifikation gesetzt
   - Kein Faktor eingerichtet → Nutzer wird nach dem Login zum Profil-Tab geleitet, rotes Banner „2FA ist erforderlich" erscheint
3. Selbst falls ein `aal1`-Token direkt als Cookie gesetzt würde (z.B. durch Skript statt Browser-Flow): `auth-gateway` `/verify` lehnt es serverseitig ab – der Bypass über das clientseitige Formular ist geschlossen.
4. Admin-/Superadmin-Endpoints verlangen zusätzlich `aal2`, unabhängig von der Rollenliste (siehe [Rollen-Hierarchie](#rollen-hierarchie)).

### Notfall-Kill-Switch

Falls die MFA-Pflicht temporär deaktiviert werden muss (z.B. Migration, Support-Fall):
```bash
# .env
MFA_REQUIRED=false
```
Danach `auth-gateway` neu starten, damit die Env-Variable greift:
```bash
docker compose up -d auth-gateway
```
**Achtung:** Damit greift wieder die alte Lücke – nur für kurze, kontrollierte Zeitfenster verwenden.

### Backup bei verlorenem TOTP-Device

Superadmins können die 2FA eines Users direkt über das Dashboard zurücksetzen: **Benutzerverwaltung → „2FA zurücksetzen"** bei der jeweiligen Zeile (ruft `POST /control/users/mfa-reset` auf, siehe [15_api_reference.md](15_api_reference.md)). Der Nutzer muss danach TOTP neu einrichten.

Alternativ manuell über die GoTrue-Admin-API (macht dasselbe, was der Endpoint intern tut):
```bash
SERVICE_KEY=$(grep "^SERVICE_ROLE_KEY=" .env | cut -d= -f2)

# Alle MFA-Faktoren eines Users auflisten
curl -s "http://localhost:8000/auth/v1/admin/users/<user-id>" \
  -H "Authorization: Bearer $SERVICE_KEY" \
  -H "apikey: $SERVICE_KEY" | jq .factors

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

## Grafana Auth-Proxy-Header

Grafana vertraut den Headern `X-Forwarded-User`/`X-Forwarded-Role` (`GF_AUTH_PROXY_*` in `docker-compose.yml`). Damit ein Client diese Header nicht selbst mitschicken kann, gilt:

- Auf allen Pfaden mit `forward_auth` überschreibt Caddy `X-Forwarded-User` per `copy_headers` mit dem vom auth-gateway verifizierten Wert – ein client-gelieferter Wert wird verworfen.
- Auf den beiden auth-freien Pfaden `/public/*` und `/avatar/*` (statische Assets, kein Login-Redirect gewünscht) entfernt Caddy die Header explizit (`header_up -X-Forwarded-User` / `-X-Forwarded-Role`), statt sie durchzureichen.
- Zusätzlich kann `GRAFANA_PROXY_WHITELIST` in `.env` gesetzt werden (IP/Subnetz des Compose-Netzes), damit Grafana die Header ohnehin nur vom Caddy-Container akzeptiert (defense-in-depth, `GF_AUTH_PROXY_WHITELIST`).

## Bekannte Einschränkungen

| Thema | Status | Begründung |
|---|---|---|
| AnonKey im Frontend | Akzeptiert | Supabase-Design-Muster; durch RLS + `DISABLE_SIGNUP=true` geschützt |
| Docker-Socket-Zugriff in auth-gateway | Notwendig | Pflicht für Service Control (start/stop) |
| `SERVICE_ROLE_KEY` in Env-Vars | Standard | Docker-Pattern; kein Fix ohne Swarm Secrets |
| CSRF-Schutz für `/control/*`-POSTs | Nicht implementiert | Nur Cookie-Auth (`SameSite=Lax`); Härtung über zusätzlichen `Authorization`-Header-Zwang ist als Folgeschritt geplant |
