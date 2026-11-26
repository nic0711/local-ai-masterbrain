# 04 – Updates und Rollback

> Status: Phase-1-Stand — Teil der laufenden Handbuchkonsolidierung
> (siehe `docs/planning/documentation-inventory.md`). Dieses Dokument
> beschreibt das Zielmodell aus ADR-0007 und verweist auf bestehende,
> gültige Dokumentation statt sie zu duplizieren.

## Bezug

- Entscheidungsgrundlage: [`docs/adr/0007-release-and-update-strategy.md`](../adr/0007-release-and-update-strategy.md)
- Bestehende, unverändert gültige Backup-Dokumentation: [`docs/08_backup_and_recovery.md`](../08_backup_and_recovery.md)
- Release-Manifest-Schema: [`release-manifest.schema.yml`](../../release-manifest.schema.yml)

## Release-Modell (Zielzustand laut ADR-0007)

- Jede Komponente hat ihre eigene SemVer-Versionierung.
- Zusätzlich existiert ein geprüftes Gesamt-Stack-Release mit Manifest
  (`release-manifest.schema.yml`), das referenziert: Image, Tag, Digest,
  SBOM-Referenz, Scan-Report-Referenz, Signaturstatus je Custom Image.
- Monatliches Stack-Release, unabhängige Security-Hotfixes dazwischen möglich.
- Kein automatisches Produktions-Deployment nach einem Wochenbuild.
- Kein `latest`-Tag in Produktion. Seit 2026-11 erfüllt: alle Images in
  `docker-compose.yml` sind exakt gepinnt, `docs/planning/image-pinning-baseline.yml`
  ist leer, CI (`scripts/ci/check-image-pinning.sh`) verhindert neue Ausnahmen.

## Rollback-Modell

- **Grundsatz:** Das aktuelle und das vorherige Stack-Release müssen jederzeit
  rollbackfähig bleiben (kein Force-Push, keine History-Umschreibung nötig).
- **Rollback eines Merges:** Revert-Commit auf `main`, keine `git reset --hard`
  auf einen bereits gepushten Branch.
- **Rollback eines Custom-Image-Deployments:** vorheriges, im Release-Manifest
  referenziertes Image-Digest erneut deployen (Digest-Pinning ist Voraussetzung,
  siehe ADR-0008 und `docs/planning/image-pinning-baseline.yml`).
- **Rollback nach Datenwiederherstellung:** siehe `docs/08_backup_and_recovery.md`
  und ADR-0006 (Lösch-Replay nach Restore, Produktivfreigabe erst nach
  erfolgreichem Smoke-Test).

## Third-Party-Image-Updates (Dependabot)

- Dependabot (`.github/dependabot.yml`, Ecosystem `docker-compose`) schlägt
  wöchentlich neue Tags für die gepinnten Images vor, höchstens zwei offene PRs.
- Jeder Bump läuft durch dieselben Pflicht-Checks wie andere PRs; der Branch
  muss vor dem Merge aktuell sein (Branch-Schutz „strict“).
- Nach dem Merge lokal: `git pull`, dann `docker compose --profile cpu up -d <service>`.

### n8n

Gemäß [n8n-Doku „Update n8n“](https://docs.n8n.io/deploy/host-n8n/keep-n8n-running/update-n8n):

1. **Vor dem Update sichern:** Datenbank (`pg_dumpall`, siehe
   [08_backup_and_recovery.md](../08_backup_and_recovery.md)) **und** die `.env`
   mit `N8N_ENCRYPTION_KEY`. Ohne den Schlüssel sind Credentials nach einem
   Restore unbrauchbar.
2. **Gemeinsam updaten:** `n8nio/n8n` und `n8nio/runners` müssen exakt dieselbe
   Version haben. Dependabot liefert beide in einem PR (Gruppe `n8n`); nie nur
   eines der beiden Images anheben.
3. **Runner-Konfiguration abgleichen:** `n8n/task-runners.json` ist eine Kopie von
   `/etc/n8n-task-runners.json` aus dem Runner-Image mit erweiterter
   `NODE_FUNCTION_ALLOW_BUILTIN`-Allowlist. Bei jedem Bump mit der Datei aus dem
   neuen Image vergleichen:
   `docker run --rm --entrypoint cat n8nio/runners:<version> /etc/n8n-task-runners.json | diff - n8n/task-runners.json`
4. **Migrationen** laufen beim Start automatisch. Ein Downgrade auf das alte Image
   macht sie **nicht** rückgängig: Rollback nur über `n8n db:revert` (vor dem
   Image-Wechsel, im laufenden Container) oder Restore des Datenbank-Backups.
5. **Major-Version 3.0** ist in Dependabot gesperrt (Breaking Changes, siehe
   [v3.0-Breaking-Changes](https://docs.n8n.io/changelog/v30-breaking-changes)).
   Vor dem Sprung die Workflows in `n8n-tool-workflows/` gegen die Liste prüfen.

## Custom-Image-Deployment ohne Repo-Cutover (Verfahren, 2026-10-25 durchgeführt)

Für `auth-gateway`, `python-nlp-service`, `ocr-service` und `tts-service` (Compose-Projekt `localai`,
`build:` ohne `image:`, implizite Namen `localai-<service>:latest`). Der Produktiv-Checkout bleibt
unverändert, denn `auth-gateway` bindet ihn als `/opt/project` ein und führt dort `docker compose` aus.

1. **Vorprüfung:** alle Container und die vier Services `healthy`, mindestens 20 GB frei, Backup geprüft (siehe `docs/08_backup_and_recovery.md`).
2. **Bauen aus separatem Worktree** von `origin/main` (nicht aus dem Produktiv-Checkout), `docker build --no-cache` mit denselben Contexts wie im Compose (`auth-gateway` und `python-nlp-service`: Repo-Root mit `-f <svc>/Dockerfile` und `--build-arg GIT_COMMIT=unknown`; `ocr-service` und `tts-service`: eigener Ordner). Tag `localai-<svc>:sec-<datum>`. Versionen im Image prüfen.
3. **Rollback-Tag** auf das laufende Image: `docker tag $(docker inspect <svc> --format '{{.Image}}') "localai-<svc>:rollback-<datum>"`. In zsh `"${s}"` statt `$s:` nutzen (`:r` wird sonst als Modifier gelesen).
4. **Cutover je Service nacheinander** (nlp, ocr, tts, zuletzt auth-gateway): `docker tag localai-<svc>:sec-<datum> localai-<svc>:latest`, dann mit allen vier Compose-Dateien (`docker-compose.yml`, `…override.public.yml`, `…override.public.supabase.yml`, `…override.none.yml`) und `-p localai`: erst `up --dry-run --no-deps --no-build <svc>` (genau ein „Recreate“), dann `up -d --no-deps --no-build <svc>`.
5. **Prüfung je Service** (Health, Funktionsaufruf, Logs). `auth-gateway` ist für alle geschützten Routen kurz nicht erreichbar (ca. 7 s).
6. **Rollback ohne Konfigurationsänderung:** `docker tag localai-<svc>:rollback-<datum> localai-<svc>:latest`, dann derselbe `up -d --no-deps --no-build <svc>`. Volumes und Mounts bleiben unberührt.
7. **Aufräumen:** Worktree entfernen. Rollback-Tags und alte Images ca. 7 Tage behalten.

Hinweis: `python-nlp-service` meldet `/ready` mit 503, solange Neo4j (Profil `optional`) nicht läuft. Das ist erwartet.
