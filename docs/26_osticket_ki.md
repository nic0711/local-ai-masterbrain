# 26 · osTicket KI-Integration

## Überblick

Zwei n8n-Workflows lesen direkt aus der osTicket-MySQL-Datenbank:

| Workflow | Datei | Läuft | Funktion |
|---|---|---|---|
| KI-Analyse | `osticket-ai-analysis.json` | alle 10 min | Offene Tickets → LLM-Lösungsvorschlag → interne Notiz |
| Wissensbasis | `osticket-to-knowledge-base.json` | täglich 02:00 | Gelöste Tickets → Neo4j + Qdrant |

---

## Setup

### 1. Qdrant-Collection anlegen

Einmalig vor dem ersten Workflow-Start:

```bash
bash scripts/init_qdrant_osticket.sh
# Standard: https://qdrant.brain.local
# Anderer Host: bash scripts/init_qdrant_osticket.sh http://localhost:6333
```

Collection: `osticket_solutions`, Dimension 768 (nomic-embed-text), Cosine-Ähnlichkeit.

### 2. MySQL-Credential in n8n anlegen

n8n → Credentials → Neu → **MySQL**:

| Feld | Wert |
|---|---|
| Name | `osTicket DB` |
| Host | osTicket-Datenbank-Host (z.B. `192.168.1.50`) |
| Port | `3306` |
| Datenbank | `osticket` (Standard-DB-Name) |
| Benutzer | Read-only MySQL-User (siehe unten) |
| Passwort | Passwort des MySQL-Users |

**Read-only MySQL-User anlegen (empfohlen):**
```sql
CREATE USER 'n8n_osticket'@'%' IDENTIFIED BY 'sicheres-passwort';
GRANT SELECT ON osticket.ost_ticket TO 'n8n_osticket'@'%';
GRANT SELECT ON osticket.ost_ticket__cdata TO 'n8n_osticket'@'%';
GRANT SELECT ON osticket.ost_thread_entry TO 'n8n_osticket'@'%';
FLUSH PRIVILEGES;
```

### 3. n8n Variables setzen

n8n → Settings → Variables:

| Variable | Wert | Verwendet in |
|---|---|---|
| `OSTICKET_HOST` | `osticket.deine-domain.de` (ohne https://) | osticket-ai-analysis |
| `OSTICKET_API_KEY` | osTicket API-Schlüssel (siehe unten) | osticket-ai-analysis |

### 4. osTicket API-Schlüssel anlegen

osTicket Admin → Admin Panel → Manage → **API Keys** → Neuer Key:
- IP-Einschränkung: n8n-Server-IP (z.B. IP des brain.local-Servers)
- Berechtigungen: `Can Create Tickets` + `Can Execute Cron`

Den generierten Key als `OSTICKET_API_KEY` in n8n speichern.

### 5. Workflows importieren und aktivieren

```
n8n → Workflows → Import
→ n8n-tool-workflows/osticket-ai-analysis.json
→ n8n-tool-workflows/osticket-to-knowledge-base.json
```

In beiden Workflows die MySQL-Credential `osTicket DB` auswählen, dann aktivieren.

---

## Workflow: KI-Analyse (alle 10 Minuten)

### Ablauf

```
Schedule (10 min)
  → MySQL: Offene Tickets der letzten 24h holen
    (Tickets mit vorhandener KI-Notiz werden ausgeschlossen)
  → SplitInBatches (1 Ticket pro Iteration)
    → Ollama: Embedding des Ticket-Texts (nomic-embed-text)
    → Qdrant: Ähnlichkeitssuche in 'osticket_solutions' (Score ≥ 0.75)
    → Code: LLM-Prompt aus Ticket + ähnlichen Lösungen bauen
    → Ollama: Lösungsvorschlag generieren (qwen2.5:7b)
    → osTicket API: Interne Notiz mit Tag [KI-Analyse] posten
```

### Duplikatsschutz

Der SQL-Query schließt Tickets aus, die bereits eine Notiz mit `[KI-Analyse]` enthalten:
```sql
AND t.id NOT IN (
  SELECT ticket_id FROM ost_thread_entry
  WHERE body LIKE '%[KI-Analyse]%' AND type = 'N'
)
```

### Relevante MySQL-Tabellen

| Tabelle | Inhalt |
|---|---|
| `ost_ticket` | Ticket-Metadaten (id, number, status_id, created) |
| `ost_ticket__cdata` | Betreff (subject), Custom Fields |
| `ost_thread_entry` | Nachrichten (type='M'), Antworten (type='R'), Notizen (type='N') |

`status_id`: 1 = offen, 2 = in Bearbeitung, 3 = gelöst/geschlossen

---

## Workflow: Wissensbasis (täglich 02:00)

### Ablauf

```
Schedule (02:00)
  → MySQL: Gelöste Tickets der letzten 7 Tage
    (GROUP_CONCAT von Fragen + Antworten pro Ticket)
  → SplitInBatches (1 Ticket pro Iteration)
    → Code: HTML-Tags bereinigen, Texte kürzen
    → Ollama: Embedding (nomic-embed-text, Dim 768)
    → Qdrant upsert (Collection 'osticket_solutions')
    → python-nlp-service /document/analyze: NER-Entitäten extrahieren
    → python-nlp-service /graph/index: Neo4j-Eintrag anlegen
```

### Qdrant-Payload-Schema

```json
{
  "number": "12345",
  "subject": "VPN verbindet sich nicht",
  "question": "...",
  "solution": "...",
  "closed_at": "2026-07-05T02:00:00"
}
```

---

## Troubleshooting

**MySQL-Verbindung schlägt fehl:**
```bash
# Connectivity testen (aus n8n-Container)
docker exec n8n nc -zv <osticket-host> 3306
# Firewall freigeben: TCP/3306 vom brain.local-Server
```

**Qdrant gibt 404 bei Ähnlichkeitssuche:**
```bash
# Collection anlegen falls noch nicht geschehen
bash scripts/init_qdrant_osticket.sh
# Status prüfen
curl https://qdrant.brain.local/collections/osticket_solutions
```

**osTicket API antwortet 401:**
- API-Key in n8n-Variable `OSTICKET_API_KEY` korrekt?
- IP-Einschränkung im osTicket-Admin: n8n-Server-IP eingetragen?

**Kein Lösungsvorschlag bei Qdrant-Score < 0.75:**
- Normal bei wenigen indizierten Tickets; Schwellwert im Query-Node anpassbar
- Nach mehr gelösten Tickets wird die Trefferquote besser
