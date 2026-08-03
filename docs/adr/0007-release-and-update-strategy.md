# ADR 0007: Komponenten-Releases plus geprüftes Stack-Release

- Status: Akzeptiert
- Datum: 2026-08-03

## Entscheidung

Jede eigene Komponente besitzt eine eigene SemVer-Version. Zusätzlich existiert
ein geprüftes Gesamt-Stack-Release mit Release-Manifest.

- monatliches Stack-Release
- Security-Hotfixes unabhängig
- tägliche CVE- und Update-Prüfung
- wöchentlicher vollständiger Rebuild aller Custom Images
- kein automatisches Produktionsdeployment
- keine produktiven `latest`-Tags

## Folgen

Sicherheitsupdates können schnell vorbereitet werden. Produktionsfreigabe,
Backupprüfung, Migrationen, Smoke-Test und Rollback bleiben kontrolliert.
