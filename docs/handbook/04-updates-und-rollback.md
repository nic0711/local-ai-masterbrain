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
- Kein `latest`-Tag in Produktion (siehe `docs/planning/image-pinning-baseline.yml`
  für den aktuellen Bestand an Third-Party-Images, die diese Vorgabe heute noch
  nicht erfüllen — Behebung ist Gegenstand von Phase 2/3, nicht dieses PR).

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

## Ausdrücklicher Hinweis zu diesem PR

Für den PR `agent/phase-1-governance-ci-supply-chain` selbst gilt: Es handelt
sich um einen Draft-PR ohne Merge. Der Rollback dieses PR ist in der PR-Beschreibung
**beschrieben, nicht durch einen tatsächlichen Merge-Rollback getestet** — ein
echter Rollback-Test setzt einen vorherigen Merge voraus, der hier bewusst nicht
stattfindet. Dies ist eine bewusste Abweichung von der in
`docs/planning/implementation-roadmap.md` genannten Formulierung "Rollback
erfolgreich" zugunsten der in `.handoff/claude/checks/PHASE-1-ACCEPTANCE.md`
verlangten Formulierung "Rollback beschrieben".
