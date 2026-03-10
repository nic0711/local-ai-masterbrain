# 8. Backup & Recovery

Das integrierte Backup-System sichert Konfigurationsdateien und n8n-Workflows direkt über das Dashboard – ohne externe Tools oder manuelle Befehle.

---

## Übersicht

| Was wird gesichert | Wo gespeichert |
|---|---|
| `n8n/backup/workflows/*.json` | `./backups/backup_YYYYMMDD_HHMMSS.tar.gz` |
| `docker-compose.yml`, `Caddyfile`, `.env.example` | gleiches Archiv |
| `auth-gateway/app.py`, `dashboard/*.js/html/css` | gleiches Archiv |
| `backup/backup*.sh` | gleiches Archiv |

**Nicht** gesichert (Datenbank-Volumes, Ollama-Modelle): diese sollten über separate Volume-Backups abgesichert werden.

---

## Backup im Dashboard

### Manuelles Backup starten

1. Dashboard öffnen → **Administration**-Tab
2. Im Backup-Panel: **„Backup jetzt starten"** klicken
3. Das Backup wird sofort erstellt (typisch < 1 Sekunde)
4. Status wechselt auf „Erfolgreich", Backup erscheint in der Liste

### Backup-Liste

Die Tabelle zeigt alle verfügbaren Backups mit:
- **Datum** – Zeitstempel der Erstellung
- **Größe** – Archivgröße
- **Dateien** – Anzahl archivierter Dateien
- **Diff** – Vergleich mit aktuellem Stand
- **Wiederherstellen** – Restore-Dialog

### Diff-Ansicht

Klick auf **„Diff"** öffnet ein Modal mit:
- Dateiliste aus dem Backup (links)
- Klick auf eine Datei → unified diff (grün = hinzugefügt, rot = entfernt)
- Badge „Geändert" / „Unverändert" pro Datei

### Restore

1. **„Wiederherstellen"** klicken → Bestätigungsdialog
2. Bestätigen → n8n-Workflows werden sofort in `n8n/backup/workflows/` zurückgeschrieben
3. Anschließend in n8n: **Settings → Import workflow** (falls Workflows bereits in n8n geladen waren)

> **Hinweis:** Restore überschreibt nur die Workflow-JSON-Dateien auf dem Dateisystem.
> In n8n laufende Workflows werden nicht automatisch neu geladen – manueller Import nötig.

---

## Automatisches Backup (optional)

Für geplante Backups den Container mit dem `backup`-Profil starten:

```bash
docker compose -p localai --profile backup up -d
```

Intervall konfigurieren in `.env`:
```bash
BACKUP_INTERVAL_H=24    # Standard: alle 24 Stunden
```

Der `backup-cron`-Container überwacht ein Trigger-File und führt zusätzlich automatische Backups aus. Der manuelle Dashboard-Button funktioniert **unabhängig** davon – auch ohne `backup`-Profil.

---

## Backups bereinigen

Automatisch: nur die letzten **10 Backups** werden behalten, ältere werden beim nächsten Backup-Lauf gelöscht.

Manuell:
```bash
ls -lh ./backups/
rm ./backups/backup_20240101_*.tar.gz ./backups/backup_20240101_*.meta.json
```

---

## Archiv-Inhalt prüfen

```bash
# Dateien im Archiv anzeigen
tar -tzf ./backups/backup_20240315_143000.tar.gz

# Einzelne Datei extrahieren
tar -xzf ./backups/backup_20240315_143000.tar.gz n8n/backup/workflows/V5_Obsidian_Vault_Sync.json
```

---

## Docker-Volume-Backup (Datenbanken)

Für vollständige Daten-Backups (Supabase-DB, Qdrant, n8n-Daten) müssen Docker-Volumes separat gesichert werden:

```bash
# Beispiel: n8n-Volume sichern
docker run --rm \
  -v localai_n8n_storage:/data:ro \
  -v $(pwd)/backups:/backup \
  alpine \
  tar czf /backup/n8n_volume_$(date +%Y%m%d).tar.gz -C /data .

# Supabase-DB via pg_dump
docker exec supabase-db pg_dump -U postgres postgres \
  > ./backups/supabase_$(date +%Y%m%d).sql
```

---

## Troubleshooting

**Backup-Button zeigt Fehler**
```bash
docker logs auth-gateway | tail -20
# Typische Ursache: ./backups/ Verzeichnis hat falsche Berechtigungen
ls -la ./backups/
```

**Backup-Liste bleibt leer nach Klick**
- auth-gateway muss neu gebaut worden sein (nach letztem Update)
- `docker compose -p localai up -d --build auth-gateway`

**Restore hat keine Wirkung in n8n**
- Restore schreibt nur Dateien – n8n muss Workflows neu importieren
- n8n → Settings → Import workflow → Datei aus `n8n/backup/workflows/` wählen
