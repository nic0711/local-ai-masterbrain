# ADR 0010: Datei-basierte Secrets mit geplanter Provider-Abstraktion

- Status: Akzeptiert
- Datum: 2026-08-03

## Entscheidung

Runtime-Secrets liegen als rootgeschützte Dateien außerhalb des Repositories.

- Verzeichnisse `0700`
- Dateien `0600`
- read-only Mounts
- nur in berechtigte Container
- keine Secrets in `.env`, Compose, Logs oder Backups

Eine spätere Secret-Provider-Schnittstelle ermöglicht Vault oder einen
vergleichbaren Secret Manager.

## Folgen

Secrets können ohne Image-Neubau rotiert werden. Der aktuelle Ein-Host-Betrieb
benötigt keinen zusätzlichen hochverfügbaren Secret-Service.
