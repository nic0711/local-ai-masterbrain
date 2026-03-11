# 12. Monitoring – UptimeBot

UptimeBot (Uptime Kuma) ist ein selbst-gehostetes Service-Monitoring-Tool als Ersatz für UptimeRobot.

## Übersicht

| Feature | Beschreibung |
|---|---|
| **Service-Monitoring** | HTTP, TCP, DNS, Ping |
| **Public Status Page** | Öffentlich erreichbar für Kunden/Team |
| **Notifications** | E-Mail, Slack, Webhook, Telegram, Discord, u.v.m. |
| **Incident-Verwaltung** | Wartungsfenster, Incident-Protokoll |
| **Uptime-Statistiken** | 24h, 7d, 30d Verfügbarkeit |

---

## Setup

### Container starten

UptimeBot läuft im `monitoring`-Profil:

```bash
docker compose -p localai --profile monitoring up -d
```

Beim ersten Aufruf unter `https://status.brain.local` wird ein Admin-Benutzer angelegt.

### Instanzname setzen

`https://status.brain.local` → **Settings → General → Instance Name** → `UptimeBot` → Save

---

## Status Page einrichten

Die öffentliche Status Page zeigt Kunden und Team den aktuellen Systemstatus.

### Erstellen

1. **Status Pages → New Status Page**
2. Name: `UptimeBot` (oder eigener Name)
3. Slug: `services` → Page erreichbar unter `https://status.brain.local/status/services`
4. **Save**

### Services hinzufügen

Über **„Add Monitor"** alle relevanten Services als Monitor anlegen, dann zur Status Page hinzufügen:

| Service | URL | Typ |
|---|---|---|
| n8n | `https://n8n.brain.local` | HTTP |
| Open WebUI | `https://webui.brain.local` | HTTP |
| Flowise | `https://flowise.brain.local` | HTTP |
| Supabase | `https://supabase.brain.local` | HTTP |
| Langfuse | `https://langfuse.brain.local` | HTTP |
| Qdrant | `https://qdrant.brain.local` | HTTP |
| SearXNG | `https://searxng.brain.local` | HTTP |

### Custom CSS einfügen (Dashboard-Theme)

1. Status Pages → deine Page → **Edit**
2. Runterscrollen zu **„Custom CSS"**
3. Inhalt von `dashboard/assets/uptime-kuma-status.css` hineinkopieren
4. **Save**

Das Theme passt dann exakt zum Dashboard: gleiche Farben, Inter-Font, Dark Mode.

---

## Notifications einrichten

### E-Mail

`Settings → Notifications → Add Notification → Email (SMTP)`

```
SMTP Host:     mail.yourdomain.com
SMTP Port:     587
Benutzername:  alerts@yourdomain.com
Passwort:      ••••••••
Von:           UptimeBot <alerts@yourdomain.com>
An:            admin@yourdomain.com
```

### Slack

`Settings → Notifications → Add Notification → Slack`

1. Slack-App anlegen unter [api.slack.com](https://api.slack.com/apps)
2. Incoming Webhook URL aus der App kopieren
3. In Uptime Kuma: Webhook URL einfügen, Kanal wählen

### Webhook (allgemein)

`Settings → Notifications → Add Notification → Webhook`

```
URL:     https://your-endpoint.com/webhook
Method:  POST
```

Payload-Format (JSON):
```json
{
  "monitor": "{{monitorName}}",
  "status": "{{status}}",
  "msg": "{{msg}}"
}
```

---

## Maintenance Windows

Für geplante Wartungen (verhindert Fehlalarme):

`Maintenance → New Maintenance` → Zeitraum + betroffene Monitore auswählen → Save

---

## Troubleshooting

**Problem: `https://status.brain.local` zeigt 502**

```bash
docker ps | grep uptime-kuma
# Falls nicht läuft:
docker compose -p localai --profile monitoring up -d uptime-kuma
```

**Problem: Monitor zeigt immer „Down" obwohl Service läuft**

- Services sind hinter `forward_auth` (Caddy) – von innen erreichbar, extern erst nach Login
- Lösung: Monitor-URL auf interne Docker-Adresse setzen, z.B. `http://n8n:5678/healthz`
- Alternativ: separaten „Heartbeat"-Monitor verwenden

**Problem: Notifications kommen nicht an**

```bash
# Notification direkt testen:
# Settings → Notifications → deine Notification → Test
docker logs uptime-kuma | tail -20
```

**Problem: Status Page nicht öffentlich erreichbar**

Caddyfile für UptimeBot verwendet bewusst **kein** `forward_auth` – die Status Page ist öffentlich.
Prüfen ob Caddy neu geladen wurde:
```bash
docker exec caddy caddy reload --config /etc/caddy/Caddyfile
```
