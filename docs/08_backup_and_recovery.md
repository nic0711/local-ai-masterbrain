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

Für geplante Backups den `backup-cron`-Container mit dem `backup`-Profil starten:

```bash
docker compose -p localai --profile backup up -d
```

Intervall konfigurieren in `.env`:
```bash
BACKUP_INTERVAL_H=24    # Standard: alle 24 Stunden
```

**Wie es funktioniert:**
- `backup-cron` läuft als schlanker Alpine-Container (kein Docker-Socket nötig)
- Prüft alle 30 Sekunden auf Trigger-Datei oder abgelaufenes Intervall
- Schreibt Status in `/opt/backups/.backup_status` → Dashboard liest ihn
- Restore-Trigger via `/opt/backups/.restore` (gesetzt durch Dashboard-Button)

Der manuelle Dashboard-Button funktioniert **unabhängig** davon – auch ohne `backup`-Profil.

### Gesicherte Dateien

| Kategorie | Dateien |
|---|---|
| Workflows | `n8n/backup/workflows/*.json` |
| Stack-Konfiguration | `docker-compose.yml`, `Caddyfile`, `.env.example` |
| Auth-Gateway | `auth-gateway/app.py`, `auth-gateway/requirements.txt` |
| Dashboard | `index.html`, `style.css`, `auth.js`, `main.js`, `health.js`, `admin.js`, `entrypoint.sh` |
| Backup-Scripts | `backup/backup-daemon.sh`, `backup/backup.sh` |

**Nicht gesichert:** Docker-Volumes (Datenbank, Modelle) → separates Volume-Backup erforderlich.

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

---

## Vollbackup vor Deployments (verifiziertes Verfahren)

Das Skript `backup/backup.sh` sichert nur Konfiguration und Workflows. Vor einem Image-Deployment
wurde zusätzlich folgendes Backup erstellt und per Restore-Probe geprüft (Ablage außerhalb des
Repos, Rechte 700, `SHA256SUMS` über alle Dateien):

| Inhalt | Verfahren |
|---|---|
| Datenbanken (logisch) | `docker exec supabase-db pg_dumpall -U postgres \| gzip` |
| Datenbank (physisch) | `pg_backup_start('label', true)`, Datenverzeichnis `supabase/docker/volumes/db/data` schreibgeschützt kopieren, `pg_backup_stop(true)` (Label als `backup_label` sichern), danach `pg_wal` erneut sichern. Alles in **einer** offenen psql-Sitzung. |
| Compose-Volumes | je `docker run --rm -v <vol>:/d:ro … tar -czf` (Socket-Dateien werden ignoriert) |
| SQLite (`webui.db`, `chroma.sqlite3`, `kuma.db`, Hermes-DBs, `grafana.db`) | SQLite-Backup-API über `file:…?mode=ro`, danach `integrity_check` und Zeilenzahl-Vergleich zur Live-DB |
| Konfiguration | `.env`, Caddyfile, Compose-Dateien samt Overrides, Supabase-`.env`, Kong, Functions, Dashboard, Grafana, Prometheus, SearXNG, n8n |

**Hinweise:**
- `pg_basebackup` funktioniert hier nicht: `pg_hba.conf` hat keinen Replikationseintrag. Die Konfiguration wurde dafür nicht geändert.
- `pg_dumpall` allein reicht nicht für einen vollständigen Restore: Rechte auf Extension-Objekte (`graphql`, `vault`, `net`) und `graphql_public.graphql` werden nicht geschrieben.
- Volume-Archive eines laufenden Systems sind keine Snapshots. SQLite-Dateien deshalb immer mit der Backup-API sichern.
- `ocr_storage` und `tts_storage` enthalten nur reproduzierbare Modell-Caches (Stand 2026-10, Ein-/Ausgabeverzeichnisse leer). Vor jedem Deployment erneut prüfen.

**Restore-Probe (Wegwerf-Container, ohne Port, außerhalb des Stack-Netzes):**
1. Physisches Backup in ein neues Volume entpacken, `backup_label` und nachgesicherte WAL-Dateien einspielen, Besitzer `105:105` (User `postgres` im Image), Rechte 700.
2. `supabase/postgres:15.8.1.085` darauf starten. Erwartet: `consistent recovery state reached`, `ready to accept connections`.
3. Katalog (Funktionen, Rechte, Trigger, Event-Trigger, Rollen, Extensions, Policies) und Zeilenzahlen aller Tabellen mit der Produktion vergleichen. Policy-Texte nur mit `set search_path=pg_catalog` vergleichen.
4. Probe-Container und -Volume entfernen.

Ein Start des gesamten Supabase-Stacks und von n8n auf den wiederhergestellten Daten wurde noch nicht getestet.
