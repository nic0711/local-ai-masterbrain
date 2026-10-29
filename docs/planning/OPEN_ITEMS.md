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

## 6. Stand 2026-10-25 (nach Security-Deployment, PR #203)

- **CVE-2026-78669 Recheck** (`golang.org/x/net` v0.58.0 in `docker-compose-plugin` 5.6.1, auth-gateway):
  `upstream-blocked.yml`, `recheck_after: 2026-11-07`. Prüfen, ob ein `docker/compose`-Release mit
  `golang.org/x/net >= 0.60.0` (Upstream-`main`, PR #14316) im offiziellen Docker-Debian-Repo verfügbar
  ist. Das ist das einzige UPSTREAM-BLOCKED-Finding der vier Custom-Images; keine Security-Exceptions aktiv.
  Die Punkte 3 und 4 oben sind historisch und gelten nur, solange ihre Einträge in der Datei stehen.
- **Issue #205:** `pip check` meldet in auth-gateway und python-nlp-service Konflikte (`python-json-logger`
  4.0.0 in `masterbrain-common` gegen 4.2.0 im Lock; `pyjwt` fehlt im nlp-Lock). CI führt kein `pip check` aus.
- **Issue #206:** TrOCR lädt im ocr-service nicht (Tokenizer-Backend, `sentencepiece`/`tiktoken` fehlt). Aktiv ist nur Tesseract.
- **OCR-Abnahme** des Deployments bestand nur aus synthetischem PNG/Bild-PDF und Unit-Tests. Pillow 13 und
  filelock 4 sind nicht mit echten Scans geprüft.
- **Aufräumen ab 2026-11-01:** Rollback-Tags `localai-<svc>:rollback-20261025` und die alten Image-IDs
  (`1fefc685c6f3`, `098afbf9f980`, `905df7adb1ed`, `941daadfb6c0`). Backup unter
  `../pgdata-backups-local-ai-masterbrain/pre-deploy-20261025-0100/` behalten.
- **Grafana** (behoben 2026-10-26): Die Restart-Schleife (`Datasource provisioning error: data source not found`)
  kam von der in `prometheus.yml` neu gesetzten `uid: prometheus`, während die Datasource in der Grafana-DB
  noch eine generierte UID hatte. Einmalig über `deleteDatasources` (Name `Prometheus`) entfernt und neu
  provisioniert. Bei einer weiteren UID-Änderung gilt dasselbe Vorgehen.
- **Container-Bereinigung zurückgestellt.** Kandidaten laut Analyse (keine Nutzung im Repo gefunden):
  `supabase-edge-functions` (nur Demo-Funktionen), `supabase-imgproxy`, `supabase-pooler`, `redis`
  (nur SearXNG, `limiter: false`), evtl. `supabase-realtime`, `uptime-kuma` gegen Blackbox-Monitoring.
  Entscheidung steht aus.
- **Produktiv-Checkout** liegt weiter auf altem Stand (`fa01b40`, Branch
  `agent/consolidate-phase-2b-and-monitoring`). Eine Umstellung auf `main` ist ein eigener Schritt
  (`auth-gateway` bindet den Checkout als `/opt/project` ein).
- **Remote-Branches:** `working` bleibt (CI-Trigger). Zwei neue Dependabot-Branches
  (`…/auth-gateway/pip-b4ce6f8da2`, `…/python-nlp-service/pip-95482ee475`) sind ungeprüft.
- **Backup/Restore:** Ein Start des gesamten Supabase-Stacks und von n8n auf wiederhergestellten Daten ist nicht getestet.

## 7. Stand 2026-10-26 (CVE-Monitoring und Image-Updates, PR #211)

- **Behebbare CRITICAL/HIGH-Funde** (`scripts/scan-running.sh`): von ca. 2300 auf 600. Der Rest steckt in
  Upstream-Images ohne neueres Release: supavisor 2.9.13 (114, Debian-Pakete), realtime v2.143.3 (80),
  storage-api v1.84.23 (32), postgres-meta v0.100.0 (45), uptime-kuma 2.5.7-slim (84, Go-Stdlib/Node),
  hermes-agent (86, Debian/Python/Node). Wöchentlich meldet `cve-watch.yml` das Issue „CVE-Watch“.
- **Nicht getestet:** echter Dashboard-Login und Storage-Upload nach dem Update (nur Health, Endpunkt- und
  API-Checks). Postgres 15.19.0.007 lief vorab an einer Datenkopie; auf Live-Daten sind `REINDEX` und
  `REFRESH COLLATION VERSION` für `postgres`, `_supabase`, `template1` ausgeführt.
- **Rollback:** Alte Images liegen lokal; storage-api und realtime haben ihr Schema vorwärts migriert,
  Rollback nur mit Dump. Postgres-Rollback auf 15.8.x braucht `chown -R 105:106` auf `localai_db-config`
  (siehe `docs/07_troubleshooting.md`). Backups: `pgdata-backups-local-ai-masterbrain/pre-update*-20261026-*`.
- **Hermes:** Bleibt auf Submodule-Pin v0.21.0; Pillow 13.0.0 und PyJWT 2.14.0 kommen über `hermes-overlay/`.
  Release v2026.9.24 brächte kaum weniger Funde (118) bei großem Config-Sprung.
- **Hermes Teams-Plattform** lädt nicht: `lazy_deps` scheitert an `microsoft-teams-apps==2.0.13.4`
  (`cryptography==50.0.0`) gegen `msal==1.36.0` (`cryptography<49`). Besteht auch mit dem Image vor dem
  Overlay; Ursache nicht abschließend geklärt.
- **Pins mit Major-Sprung** (postgrest 16.5, imgproxy 4.0.19) weichen vom Supabase-Upstream-Stand ab
  (dort postgrest v14.18, imgproxy v3.31.4). Release Notes gegen die eigene Config geprüft, API/Bild-Skalierung
  getestet; bei Auffälligkeiten in `docker-compose.override.public.supabase.yml` zurücksetzen.
- **uptime-kuma** läuft als `2.5.7-slim` (ohne Chromium, keine Browser-Monitore); die Instanz war leer.

## Nicht Teil dieser Liste

- Der lokale, produktive Checkout unter `/Users/lupus/AI/CLAUDE/local-ai-masterbrain`
  mit Branch `agent/phase-2b-python-nlp-hardening` bleibt bestehen (siehe
  Stabilisierungs-Backup) und ist die Referenz für Punkt 1/2 bei
  Wiederaufnahme.
- `session-log/` (lokal, gitignored) im selben Checkout dokumentiert den
  Ablauf des vorangegangenen Recovery-Vorfalls und die daraus gezogenen
  Lektionen — bei Bedarf dort nachlesen, nicht Teil dieses Repos.
