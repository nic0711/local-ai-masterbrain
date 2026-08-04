# ADR 0006: Restic-Backup, Restore-Tests und Lösch-Replay

- Status: Akzeptiert
- Datum: 2026-08-03

## Entscheidung

Tägliche Backups erfolgen über Restic auf lokale und verschlüsselte Offsite-
Ziele. Monatlich wird die Datenbank isoliert wiederhergestellt. Halbjährlich
wird der vollständige Stack neu aufgebaut.

RPO: 24 Stunden.
RTO: 4 Stunden.

Backups werden nach personenbezogenen Löschungen nicht verändert. Nach jedem
Restore wird ein dauerhaftes Löschregister erneut angewendet.

## Folgen

Backup-Integrität bleibt erhalten. Produktivfreigabe nach Restore ist erst nach
erfolgreichem Lösch-Replay und Smoke-Test zulässig.
