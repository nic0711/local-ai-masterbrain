# 11. Obsidian-Integration

Der Stack integriert Obsidian als persönliche Wissensdatenbank über die **Local REST API** (Plugin). KI-Agenten können Notizen lesen, verbessern und zurückschreiben. n8n indexiert den Vault in Qdrant für RAG-Abfragen.

---

## Voraussetzungen

- Obsidian läuft lokal (Mac/Linux)
- Plugin **Local REST API** installiert und aktiv (Port 27123 HTTP, 27124 HTTPS)
- API-Key aus dem Plugin-Fenster kopieren

### REST API testen

```bash
curl http://localhost:27123/vault/ \
  -H "Authorization: ApiKey DEIN_API_KEY"
# Gibt Dateiliste des Vaults zurück
```

---

## Dashboard-Kachel

Die Obsidian-Kachel im Dashboard (Bereich „Infrastructure & Data"):

- **Klick** öffnet Obsidian direkt via `obsidian://` URI
- **Health-Dot** zeigt ob die REST API erreichbar ist:
  - 🟢 Grün: Obsidian läuft, REST API antwortet (auch 401 = aktiv)
  - 🔴 Rot: Obsidian nicht gestartet oder Plugin deaktiviert

> Der Health-Check läuft intern via `host.docker.internal:27123`. Obsidian muss dafür gestartet sein.

---

## n8n Credentials einrichten

Vor der Nutzung der Workflows einmalig in n8n:

1. n8n öffnen → **Credentials → New Credential**
2. Typ: **Header Auth**
3. Name: `Obsidian REST API Key`
4. Header Name: `Authorization`
5. Header Value: `ApiKey DEIN_API_KEY`
6. Speichern

---

## V5: Obsidian Vault Sync → Qdrant

**Datei:** `n8n/backup/workflows/V5_Obsidian_Vault_Sync.json`

Indexiert Markdown-Dateien aus dem Vault in die Qdrant-Collection `obsidian_vault` für RAG-Abfragen.

### Ablauf

```
Schedule (täglich) / Webhook (manuell)
  → GET vault/ – Dateiliste holen
  → Filter: nur 20_Wissen/*.md, keine .excalidraw.md
  → Batches à 10 Dateien
  → GET vault/{path} – Inhalt lesen
  → Code: Frontmatter parsen, Markdown bereinigen
  → Text Splitter (500 Token, 50 Overlap)
  → Ollama Embeddings (nomic-embed-text)
  → Qdrant Upsert → Collection "obsidian_vault"
```

### Importieren & konfigurieren

1. n8n → **Workflows → Import from File** → `V5_Obsidian_Vault_Sync.json`
2. Credential `Obsidian REST API Key` zuweisen (HTTP Request Nodes)
3. Qdrant-Credential zuweisen
4. Ollama-Credential zuweisen
5. Optional: Filter anpassen (Zeile `20_Wissen/` im Filter-Node)

### Manuell triggern

```bash
curl -X POST https://n8n.brain.local/webhook/obsidian-vault-sync \
  -H "Authorization: Bearer DEIN_JWT"
```

### Vault-Pfade (Phase 2)

Standardmäßig wird nur `20_Wissen/` indexiert (sauberste Notizen).
Für `10_Projekte/` den Filter-Node anpassen:
```
OR: filePath.includes('10_Projekte/')
```

---

## V6: Note Optimizer – KI verbessert Notizen

**Datei:** `n8n/backup/workflows/V6_Obsidian_Note_Optimizer.json`

KI liest eine Notiz, verarbeitet sie und schreibt das Ergebnis zurück.

### Webhook-API

```bash
curl -X POST https://n8n.brain.local/webhook/obsidian-optimize \
  -H "Content-Type: application/json" \
  -d '{
    "path": "20_Wissen/KI/RAG-Systeme.md",
    "task": "improve"
  }'
```

### Verfügbare Tasks

| Task | Beschreibung | Schreibt zurück? |
|---|---|---|
| `improve` | Bessere Struktur, klarere Formulierungen | Ja (überschreibt) |
| `summarize` | 3–5-Satz-Zusammenfassung | Nein (hängt an) |
| `tag` | Tags aus Inhalt vorschlagen | Nein (gibt nur Vorschlag) |
| `connect` | Fehlende Wiki-Links vorschlagen | Nein (gibt nur Vorschlag) |

### Workflow importieren

1. n8n → **Import** → `V6_Obsidian_Note_Optimizer.json`
2. Credential `Obsidian REST API Key` zuweisen
3. Ollama-Credential zuweisen
4. Modell wählen (Standard: `llama3.2`, für bessere Qualität: größeres Modell)

---

## Direkte Nutzung via Claude Code

Claude Code kann den Vault direkt über MCP lesen und bearbeiten (kein n8n nötig):

```
# Notiz lesen
obsidian_get_file_contents("20_Wissen/KI/RAG-Systeme.md")

# Vault durchsuchen
obsidian_simple_search("RAG embedding")

# Notiz bearbeiten
obsidian_patch_content("20_Wissen/KI/RAG-Systeme.md", neuer_inhalt)
```

---

## Vault-Struktur (LYT)

| Ordner | Inhalt | Indexiert |
|---|---|---|
| `00_Inbox/` | Neue, unsortierte Notizen | Phase 2 |
| `10_Projekte/` | Aktive Projekte | Phase 2 |
| `20_Wissen/` | Permanente Notizen | ✅ Phase 1 |
| `30_Ressourcen/` | Referenzmaterial | – |
| `90_Archiv/` | Abgeschlossenes | – |

---

## Troubleshooting

**Health-Dot bleibt rot obwohl Obsidian läuft**
- REST API Plugin aktiv? Obsidian → Settings → Community Plugins → Local REST API
- Port 27123 offen? `curl http://localhost:27123/vault/ -H "Authorization: ApiKey KEY"`
- Docker Desktop muss `host.docker.internal` auflösen können

**V5 Workflow schlägt fehl**
```bash
# REST API direkt testen
curl http://localhost:27123/vault/20_Wissen/test.md \
  -H "Authorization: ApiKey DEIN_KEY"

# n8n Logs
docker logs n8n | grep -i obsidian
```

**Qdrant Collection nicht vorhanden**
```bash
# Collection erstellen (einmalig)
curl -X PUT http://qdrant.brain.local/collections/obsidian_vault \
  -H "Content-Type: application/json" \
  -d '{"vectors": {"size": 768, "distance": "Cosine"}}'
```
