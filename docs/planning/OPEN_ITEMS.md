# Offene Themen (Stand 2026-09-03, Stabilisierungslauf)

Reine Dokumentation nicht umgesetzter Themen aus dem Repository-Stabilisierungs-
und Archivierungslauf vom 2026-09-03. Keine unfertigen Implementierungen wurden
übernommen — dies ist eine Liste, keine Codeänderung.

## 1. Intune/Grafana-Geräteinventar (Erweiterung)

Auf dem historischen Branch `agent/phase-2b-python-nlp-hardening` (lokal unter
`/Users/lupus/AI/CLAUDE/local-ai-masterbrain`, dort weiterhin uncommittet)
liegt eine Erweiterung des bereits gemergten Intune/Grafana-Dashboards (PR #121):

- `.env.example`: `GRAFANA_PG_PASSWORD` für eine zusätzliche Postgres-
  Datasource (Rolle `grafana_intune_reader`)
- `docker-compose.yml`: `GRAFANA_PG_PASSWORD`-Env für den Grafana-Service
- `docs/28_intune_inventory.md`, `grafana/dashboards/intune-device-inventory.json`,
  `grafana/provisioning/datasources/postgres.yml`,
  `n8n-tool-workflows/intune-device-sync.json` (untracked)

Vollständig als Backup gesichert:
`BACKUP-local-ai-masterbrain-20260903/wip/` (`tracked-wip.diff`,
`untracked-wip.tar.gz`). Muss bei Wiederaufnahme als eigener PR gegen
aktuellen `main` aufgesetzt werden — nicht direkt aus dem alten Branch
übernehmen (Branch enthält weitere, bereits anderweitig erledigte Commits).

## 2. SearXNG `cap_drop` / First-Run-Thema

Ebenfalls im selben uncommitteten WIP: `docker-compose.yml` hatte `cap_drop:
ALL` für den SearXNG-Service auskommentiert ("Temporarily disabled for
SearXNG first run"). Ungeklärt, ob das dauerhaft nötig ist oder nur für den
initialen Start. Vor Wiederaufnahme klären, ob SearXNG mit vollem `cap_drop`
sauber initialisiert und der Grund für das ursprüngliche Deaktivieren noch
zutrifft.

## 3. CVE-2026-56854 Recheck (`golang.org/x/crypto` in `docker-compose-plugin`)

`docs/planning/security/upstream-blocked.yml`, Eintrag `recheck_after:
2026-09-07`. Prüfen: neuere `docker-compose-plugin`-Version im offiziellen
Docker-Debian-Repo verfügbar? `docker/compose`-Release mit gefixter
`golang.org/x/crypto`-Version (>= 0.55.0) getaggt?

## 4. CVE-2026-84304 Recheck (`google.golang.org/grpc` in `docker-compose-plugin`)

Gleiche Datei, `recheck_after: 2026-09-10`. Zum Zeitpunkt der Doku (2026-09-03)
lag der Fix (`grpc >= 1.83.1`) bereits auf `docker/compose` `main` (aktuell
`v1.83.2`), aber in keinem getaggten Release. Prüfen, ob inzwischen ein neues
Release existiert.

## 5. Weitere noch offene Branch-Inhalte

Vollständiger Branch-Abgleich (Phase 0 des Stabilisierungslaufs, Backup-Bundle
`01-repository-before-cleanup.bundle`) ergab: alle sonstigen Remote-Branches
sind bereits über Squash-Merge vollständig in `main` enthalten
(`gh pr list --state all` je Branch verifiziert). Kein weiterer offener
Branch-Inhalt außer den oben genannten Punkten 1–4.

## Nicht Teil dieser Liste

- Der lokale, produktive Checkout unter `/Users/lupus/AI/CLAUDE/local-ai-masterbrain`
  mit Branch `agent/phase-2b-python-nlp-hardening` bleibt bestehen (siehe
  Stabilisierungs-Backup) und ist die Referenz für Punkt 1/2 bei
  Wiederaufnahme.
- `session-log/` (lokal, gitignored) im selben Checkout dokumentiert den
  Ablauf des vorangegangenen Recovery-Vorfalls und die daraus gezogenen
  Lektionen — bei Bedarf dort nachlesen, nicht Teil dieses Repos.
