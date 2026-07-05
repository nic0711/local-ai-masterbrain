# 25 · Teams Bot + Asana-Integration

## Überblick

Zwei Integrationsebenen:

| Workflow | Datei | Funktion |
|---|---|---|
| Teams Bot | `teams-bot.json` | Chat-Antworten via Azure Bot Service + Ollama LLM |
| Grafana → Teams | `teams-grafana-alerts.json` | Monitoring-Alerts als Adaptive Cards |
| Asana Sync | `asana-sync.json` | Tägliche Task-Zusammenfassung in Teams |

---

## 1. Teams Bot (LLM-Antworten)

### Azure App Registration

1. [Azure Portal](https://portal.azure.com) → **App-Registrierungen** → Neue Registrierung
   - Name: `brain-local-teams-bot`
   - Unterstützte Kontotypen: *Konten in einem beliebigen Organisationsverzeichnis*
2. Nach Erstellung: **Zertifikate und Geheimnisse** → Neuer geheimer Clientschlüssel → Wert kopieren
3. Notieren: `Application (client) ID` + `Client Secret`

### Azure Bot Service

1. [Azure Portal](https://portal.azure.com) → **Bot Services** → Erstellen → **Azure Bot**
   - Bot Handle: `brain-local-bot`
   - App-ID: die registrierte App von Schritt 1
2. **Kanäle** → Microsoft Teams → Aktivieren (speichern)
3. **Konfiguration** → Messaging-Endpunkt setzen:
   ```
   https://n8n.brain.local/webhook/teams-bot
   ```

### n8n Einrichtung

1. **Workflow importieren**: n8n → Workflows → Importieren → `teams-bot.json`
2. **Variablen** setzen (n8n → Settings → Variables):
   ```
   TEAMS_APP_ID     = <Application ID aus App Registration>
   TEAMS_APP_SECRET = <Client Secret>
   ```
3. Workflow aktivieren (Toggle oben rechts)
4. Webhook-URL wird angezeigt unter: `https://n8n.brain.local/webhook/teams-bot`

### Test

Im Teams-Kanal die Bot-App hinzufügen (über App-Katalog oder direkte Installation) und eine Nachricht schicken. Der Bot antwortet via Ollama `qwen2.5:7b`.

### Intents erweitern

Der Knoten „Activity prüfen" in `teams-bot.json` kann mit Intent-Erkennung erweitert werden:

```javascript
// Einfaches Keyword-Routing
const text = body.text.toLowerCase();
if (text.includes('ticket')) intent = 'ticket-query';
else if (text.includes('asana')) intent = 'asana-query';
else intent = 'llm-generic';
```

---

## 2. Grafana Alerts → Teams

Dieser Weg ist einfacher als der Bot – kein Azure Bot Service nötig.

### Teams Incoming Webhook einrichten

1. Teams → gewünschter Kanal → `...` → Connectors → **Incoming Webhook** → Konfigurieren
2. Name: `Grafana Alerts`, Icon optional
3. URL kopieren (Format: `https://xxx.webhook.office.com/...`)

### n8n Einrichtung

1. Workflow importieren: `teams-grafana-alerts.json`
2. n8n Variable setzen:
   ```
   TEAMS_ALERT_WEBHOOK_URL = <Incoming Webhook URL>
   ```
3. Workflow aktivieren → Webhook-URL: `https://n8n.brain.local/webhook/grafana-alert`

### Grafana konfigurieren

1. Grafana → Alerting → Contact Points → Neuer Kontaktpunkt
   - Name: `Teams via n8n`
   - Typ: `Webhook`
   - URL: `https://n8n.brain.local/webhook/grafana-alert`
   - HTTP-Methode: POST
2. Grafana → Alerting → Notification Policies → Default Policy → Kontaktpunkt: `Teams via n8n`

Alerts erscheinen als Adaptive Cards mit Status-Farbe (Rot = Firing, Grün = Resolved).

---

## 3. Asana-Integration

### Asana Credential in n8n

1. n8n → Credentials → Neue Credential → **Asana API**
2. Access Token: [Asana → Profil → Developer Apps → Personal Access Token](https://app.asana.com/0/developer-console)
3. Credential speichern als `Asana`

### n8n Einrichtung

1. Workflow importieren: `asana-sync.json`
2. Im Knoten „Asana Tasks holen" die Credential `Asana` auswählen
3. n8n Variables setzen:
   ```
   ASANA_PROJECT_ID        = <Projekt-GID aus Asana-URL>
   TEAMS_ALERT_WEBHOOK_URL = <Incoming Webhook URL> (gleiche wie Grafana-Alert)
   ```
4. Workflow aktivieren → läuft täglich 08:00

### Asana Projekt-GID finden

In der Asana-URL: `https://app.asana.com/0/**1234567890123**/...` – die Zahl ist die Project-GID.

### Was wird gesendet

Täglich um 08:00 prüft n8n alle offenen Tasks:
- Überfällige Tasks (due_on < heute) → rot markiert
- Tasks fällig in ≤ 3 Tagen → gelb markiert
- Kein Eintrag → keine Nachricht (Stille ist gut)

---

## Sicherheitshinweise

### Was der Workflow absichert

| Schutz | Implementierung |
|---|---|
| SSRF-Schutz | `serviceUrl` wird gegen eine Allowlist bekannter Microsoft Bot Framework Domains geprüft – verhindert Token-Exfiltration an beliebige URLs |
| Webhook-Auth | Bearer-Token-Format-Check im ersten Code-Knoten – blockt anonyme POST-Anfragen ohne Authorization-Header |
| Prompt-Injection | Text auf 1000 Zeichen begrenzt; System-Prompt mit expliziter Anweisung, Rollenwechsel-Versuche zu ignorieren |

### Bekannte Einschränkung: JWT-Signaturprüfung

Der Workflow prüft nur das **Format** des Bot-Framework-JWT, nicht die **kryptografische Signatur**. Eine vollständige Verifikation erfordert:
1. HTTP-Aufruf an `https://login.botframework.com/v1/.well-known/keys` (JWKS-Endpoint)
2. Signaturprüfung mit dem passenden Public Key

Für ein internes Team-Setup (keine öffentliche Exponierung) ist der Format-Check + serviceUrl-Allowlist ausreichend. Für internet-exponierte Endpunkte die vollständige JWT-Verifikation als zusätzlichen HTTP-Node implementieren.

### Erreichbarkeit (Azure Bot Service → n8n)

Azure Bot Service muss den n8n-Webhook-Endpunkt aus dem Internet erreichen. Optionen:
- **Cloudflare Tunnel**: `cloudflared tunnel --url https://n8n.brain.local` → öffentliche URL in Azure Bot Service eintragen
- **Reverse Proxy + öffentliche Domain**: Caddy auf dem Server mit Let's Encrypt + Port 443 öffentlich
- **ngrok** (für Tests): `ngrok http https://n8n.brain.local`

## n8n Variables Übersicht

| Variable | Wert | Verwendet in |
|---|---|---|
| `TEAMS_APP_ID` | Azure App Client-ID | teams-bot |
| `TEAMS_APP_SECRET` | Azure App Client Secret | teams-bot |
| `TEAMS_ALERT_WEBHOOK_URL` | Teams Incoming Webhook URL | grafana-alerts, asana-sync |
| `ASANA_PROJECT_ID` | Asana Projekt-GID | asana-sync |

Variablen setzen: n8n → Settings → Variables → Variable hinzufügen.

---

## Troubleshooting

**Bot antwortet nicht:**
```bash
# n8n-Logs prüfen
docker compose logs n8n | tail -50
# Webhook-URL in Azure Bot Service korrekt?
# Workflow aktiv?
```

**Token-Fehler (401 vom Bot Framework):**
- App-ID und Secret in n8n-Variablen prüfen
- App Registration: Richtiger Tenant und Scope (`https://api.botframework.com/.default`)

**Asana-Fehler 403:**
- Personal Access Token abgelaufen oder fehlt Projekt-Berechtigung
- Credential in n8n aktualisieren

**Teams Webhook sendet nicht:**
- Incoming Webhook URL in Teams noch aktiv? (Connectors können deaktiviert werden)
- n8n-Variable `TEAMS_ALERT_WEBHOOK_URL` gesetzt?
