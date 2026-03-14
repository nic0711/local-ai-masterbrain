# 16. Scraping Configurator

Der **Scraping Configurator** ist ein konfigurierbarer N8N-Workflow, der Crawl4AI-Scraping
mit flexibler Ausgabe in mehrere Ziele kombiniert – ohne pro URL einen eigenen Workflow zu bauen.

**Datei:** `n8n-tool-workflows/scraping-configurator.json`
**Webhook:** `POST /webhook/scraping-config`

---

## Architektur

```
POST /webhook/scraping-config
    │
    ▼
Validate Input (Code node)
    │
    ▼
Switch: mode
    ├── css    → Crawl4AI CSS Selector   (direkte CSS-Extraktion)
    ├── llm    → Crawl4AI LLM Extract    (Ollama-gesteuerte Extraktion)
    └── auto   → Try CSS → CSS Result OK?
                   ├── OK  → weiter
                   └── NO  → Fallback LLM
    │
    ▼
Merge Results → Normalise Content
    │
    ▼
Switch: destination
    ├── supabase → POST supabase-kong:8000/rest/v1/scraped_content
    ├── neo4j    → MERGE Document-Node (Bolt HTTP API)
    ├── qdrant   → PUT /collections/{collection}/points
    ├── sheets   → Google Sheets append
    ├── webhook  → POST to caller URL
    └── all      → Supabase + Neo4j parallel
    │
    ▼
Build Response → Respond 200 JSON
```

---

## Input-Schema

**Content-Type:** `application/json`

```json
{
  "url": "https://example.com/article",
  "mode": "css",
  "css_selector": ".article-body",
  "llm_instruction": "Extrahiere Hauptinhalt und Schlüsselpunkte.",
  "destination": "supabase",
  "collection": "articles",
  "webhook_url": "https://my-app.com/scrape-callback",
  "metadata": { "project": "research", "tags": ["news"] }
}
```

| Feld | Typ | Pflicht | Default | Beschreibung |
|------|-----|---------|---------|--------------|
| `url` | string | ✅ | – | Zu scrapende URL |
| `mode` | string | – | `auto` | `css` \| `llm` \| `auto` |
| `css_selector` | string | – | `body` | CSS-Selektor (nur `css`/`auto`) |
| `llm_instruction` | string | – | Standard-Prompt | LLM-Extraktion-Anweisung |
| `destination` | string | – | `supabase` | Ziel(e) für die Daten |
| `collection` | string | – | `default` | Qdrant-Collection-Name |
| `webhook_url` | string | ⚠️ | – | Pflicht wenn `destination=webhook` |
| `metadata` | object | – | `{}` | Durchgereichte Metadaten |

---

## Modes

### `css` – CSS Selector Extraktion
Schnell, deterministisch. Erfordert einen stabilen CSS-Selektor.

```bash
curl -X POST http://n8n.brain.local/webhook/scraping-config \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://blog.example.com/post/1",
    "mode": "css",
    "css_selector": ".post-content",
    "destination": "supabase"
  }'
```

### `llm` – LLM-gesteuerte Extraktion
Flexibel, KI-basiert. Nutzt Ollama (im Stack) für die Extraktion.
Ideal für komplexe Seiten ohne stabilen DOM.

```bash
curl -X POST http://n8n.brain.local/webhook/scraping-config \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://news.example.com/",
    "mode": "llm",
    "llm_instruction": "Extrahiere alle Artikel-Titel und Teaser.",
    "destination": "neo4j"
  }'
```

### `auto` – Automatischer Fallback
Versucht zuerst CSS-Extraktion. Schlägt diese fehl (kein/leerer Content),
fällt der Workflow automatisch auf LLM zurück.

```bash
curl -X POST http://n8n.brain.local/webhook/scraping-config \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://dynamic-spa.example.com/",
    "mode": "auto",
    "destination": "supabase"
  }'
```

---

## Destinations

### `supabase`
Speichert in Tabelle `scraped_content` (Supabase PostgREST).

Benötigte `.env`-Variablen:
```bash
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_KEY=...
```

Erwartetes Tabellen-Schema:
```sql
CREATE TABLE scraped_content (
  id          BIGSERIAL PRIMARY KEY,
  url         TEXT NOT NULL,
  title       TEXT,
  content     TEXT,
  content_length INTEGER,
  mode_used   TEXT,
  metadata    JSONB DEFAULT '{}',
  scraped_at  TIMESTAMPTZ DEFAULT now()
);
```

### `neo4j`
Erstellt oder aktualisiert einen `Document`-Node im Knowledge Graph via Bolt HTTP API.

```cypher
MERGE (d:Document {url: $url})
SET d.title = $title, d.content = $content, d.scraped_at = $scraped_at
```

Benötigte `.env`-Variable:
```bash
NEO4J_BASIC_AUTH=bmVvNGo6cGFzc3dvcmQ=   # Base64 von "neo4j:password"
```

### `qdrant`
Speichert als Point in einer Qdrant-Collection.
**Hinweis:** Kein Embedding wird automatisch generiert – der Vektor-Slot bleibt leer.
Für vollständiges RAG-Retrieval zuerst Embeddings generieren (z.B. via python-nlp-service).

### `sheets`
Fügt eine Zeile in ein Google Sheet ein.

Benötigte Konfiguration: Google Sheets OAuth2 Credential in N8N (`google-sheets-creds`).
Benötigte `.env`-Variable:
```bash
GOOGLE_SHEETS_ID=1BxiMVs0XRA...  # Sheet-ID aus der URL
```

### `webhook`
Sendet das Scraping-Ergebnis als JSON-POST an eine beliebige URL.

```bash
curl -X POST http://n8n.brain.local/webhook/scraping-config \
  -d '{
    "url": "https://example.com",
    "mode": "auto",
    "destination": "webhook",
    "webhook_url": "https://my-app.example.com/api/scrape"
  }'
```

### `all`
Schreibt gleichzeitig in Supabase und Neo4j (parallele Ausführung).

---

## Response-Format

**HTTP 200 OK**
```json
{
  "success": true,
  "request_id": "sc_1710503600000",
  "url": "https://example.com/article",
  "mode": "css",
  "destination": "supabase",
  "content_length": 4820,
  "title": "Artikel-Titel",
  "scraped_at": "2026-03-15T12:00:00.000Z"
}
```

**HTTP 500 (Validate Input Fehler)**
```json
{
  "message": "Missing required field: url"
}
```

---

## Import & Aktivierung

1. N8N öffnen → **Workflows → Import from File**
2. `n8n-tool-workflows/scraping-configurator.json` hochladen
3. Workflow **aktivieren** (Toggle oben rechts)
4. Optional: Credentials für Google Sheets hinterlegen

---

## Unterschied zu bestehenden Workflows

| Workflow | Zweck | Konfigurierbar |
|----------|-------|---------------|
| `crawl4ai-scraper.json` | Webshop-Produkt-Scraper (hardcoded URL + Google Sheets) | ❌ |
| `web-scraping-to-vector-workflow.json` | Scrapen + Embedding + Neo4j + Supabase | Teilweise |
| `scraping-configurator.json` | Universaler Scraper: URL, Mode, Destination per Request | ✅ |
