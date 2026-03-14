# 13. GraphRAG – Knowledge Graph mit Neo4j

GraphRAG ergänzt die Vektorsuche (Qdrant) um einen strukturierten Knowledge Graph (Neo4j).
Dabei werden Entitäten (Personen, Orte, Konzepte), Tags und Wikilinks aus Obsidian-Notizen
als Graphstruktur gespeichert und bei RAG-Abfragen zusätzlich zur Vektorsuche genutzt.

---

## Architektur

```
Obsidian Vault
    │
    ▼
V7 Graph Indexing Workflow (n8n)
    │  • liest Markdown aus Obsidian REST API
    │  • parst Frontmatter, Tags, Wikilinks
    │
    ▼
Python NLP Service  (/graph/index)
    │  • spaCy NER → Entitäten extrahieren
    │  • Neo4j Bolt → Nodes + Beziehungen schreiben
    │
    ▼
Neo4j Graph
    (:Note) -[:MENTIONS]→ (:Entity)
    (:Note) -[:HAS_TAG]→  (:Tag)
    (:Note) -[:LINKS_TO]→ (:Note)

                    ▲
                    │
V3 RAG Agent  (Tool: Graph Query)
    │  • POST /graph/query → findet Notizen via Entitäten & Titel
    │  • kombiniert Ergebnis mit Qdrant-Vektorsuche
    ▼
Antwort an User
```

---

## Setup

### 1. NEO4J_AUTH konfigurieren

In `.env` (Passwort anpassen):
```bash
NEO4J_AUTH=neo4j/your_secure_password
```

Das Python NLP Service liest dieselbe Variable automatisch aus (`NEO4J_AUTH` + `NEO4J_URI`).

### 2. Stack starten

Neo4j läuft ohne extra Profil (immer aktiv):
```bash
docker compose -p localai up -d neo4j python-nlp-service
```

Neo4j Web UI: `https://neo4j.brain.local`
Anmeldung: Benutzername `neo4j`, Passwort aus `NEO4J_AUTH`.

### 3. Graph initialisieren

Constraints und Indexes anlegen (einmalig):
```bash
curl -X POST http://localhost:5000/graph/init
# oder via n8n: V7 Workflow starten
```

### 4. V7 Workflow in n8n importieren

1. n8n → **Workflows → Import from File**
2. `n8n/backup/workflows/V7_Graph_Indexing.json` hochladen
3. Credential **"Obsidian REST API Key"** hinterlegen (gleiche wie in V5)
4. Workflow aktivieren (läuft täglich + manuell via Webhook)

---

## Graph-Schema

| Node | Properties |
|------|-----------|
| `(:Note)` | `path`, `title`, `vault`, `updated` |
| `(:Entity)` | `name`, `label` (PER/ORG/LOC/MISC) |
| `(:Tag)` | `name` |

| Beziehung | Bedeutung |
|-----------|-----------|
| `(Note)-[:MENTIONS]->(Entity)` | Notiz erwähnt Entität |
| `(Note)-[:HAS_TAG]->(Tag)` | Notiz hat Tag |
| `(Note)-[:LINKS_TO]->(Note)` | Wikilink `[[Notiz]]` |

---

## Python NLP Service Endpoints

### POST /graph/init
Erstellt Constraints und Indexes (idempotent).

### POST /graph/index
Indexiert eine Notiz in Neo4j.
```json
{
  "path": "20_Wissen/KI/LLMs.md",
  "title": "LLMs",
  "text": "Large Language Models sind...",
  "tags": ["ki", "llm"],
  "vault": "personal",
  "lang": "de"
}
```
Response:
```json
{
  "status": "ok",
  "entities_indexed": 5,
  "tags_indexed": 2,
  "links_indexed": 3
}
```

### POST /graph/query
Findet Notizen über Entitäten und Titel.
```json
{
  "query": "OpenAI GPT-4",
  "limit": 10
}
```
Response:
```json
{
  "results": [
    {
      "path": "20_Wissen/KI/LLMs.md",
      "title": "LLMs",
      "vault": "personal",
      "score": 8,
      "matched_entities": ["OpenAI", "GPT-4"],
      "tags": ["ki", "llm"]
    }
  ],
  "total": 1
}
```

---

## RAG Agent Integration

Der V3 RAG Agent hat drei Tools:
1. **Postgres PGVector Store** – allgemeine Wissensdatenbank (hochgeladene Dokumente)
2. **Qdrant Obsidian Vault** – Obsidian-Notizen als Vektoren (semantische Ähnlichkeit)
3. **Graph Query Tool** – Obsidian Knowledge Graph (Entitäten + Verbindungen)

Der Agent entscheidet automatisch, welches Tool er für welche Frage nutzt.
Bei personenbezogenen Fragen oder Anfragen zu konkreten Entitäten wird meist
der Graph Query Tool zusätzlich zur Vektorsuche aktiviert.

---

## Troubleshooting

**Neo4j startet nicht**
```bash
docker logs neo4j | tail -30
# Typische Ursache: Heap-Speicher zu groß für verfügbaren RAM
# Lösung: NEO4J_server_memory_heap_max__size in docker-compose.yml reduzieren
```

**Graph-Indexierung schlägt fehl**
```bash
docker logs python-nlp-service | grep graph
# Häufige Ursachen:
# - NEO4J_AUTH falsch (user/password Format)
# - Neo4j noch nicht bereit (wartet auf Start)
# - Bolt-Port 7687 nicht erreichbar vom Container
```

**Graph Query liefert keine Ergebnisse**
- Erst V7 Workflow ausführen, um Notizen zu indexieren
- Neo4j Web UI prüfen: `https://neo4j.brain.local` → Node-Count
- Test direkt: `curl -X POST http://localhost:5000/graph/query -H "Content-Type: application/json" -d '{"query":"test"}'`

**Constraints-Fehler bei /graph/init**
```
Neo4j < 4.4: IF NOT EXISTS nicht unterstützt
```
→ Neueres Neo4j-Image verwenden (neo4j:latest ist 5.x)
