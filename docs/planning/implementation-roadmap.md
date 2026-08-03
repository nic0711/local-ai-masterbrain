# Umsetzungsplan

## Grundregel

Die Phasen werden nacheinander freigegeben. Offene Critical- oder High-Findings
blockieren. Ausnahmen benötigen den definierten Security-Freigabeprozess.

## Phase 1: Governance, CI und Supply Chain

### Aufgaben

- Branchschutz und Squash-Merge
- Pflicht-CI
- CODEOWNERS
- Secret Scanning und Push Protection
- Trivy, SARIF, CycloneDX
- Image-Signaturen
- Release-Manifest
- Security-Ausnahmeprozess

### Abnahme

- direkte Commits und Force-Pushes gesperrt
- Pflichtchecks blockieren Merge
- Test-Secret wird blockiert
- Beispielimage gebaut, gescannt, signiert
- Critical/High blockiert Test-Release
- Rollback erfolgreich

## Phase 2: Custom Container härten

### Aufgaben

- Base-Image-Familien
- exakte Digests und Lockfiles
- Non-root
- Capabilities reduzieren
- Health/Ready/Metrics
- Ressourcenlimits
- `masterbrain-common`
- Unit/API/Integration/Smoke

### Abnahme

- reproduzierbare Builds
- keine offenen Critical/High-Findings
- Services laufen soweit möglich non-root
- Common-Paket versioniert und gepinnt
- Pflicht-Smoke-Tests erfolgreich

## Phase 3: Betrieb vereinheitlichen

### Aufgaben

- JSON-Logs und Correlation IDs
- zentrale Grafana-Auswertung
- Teams-Alarmierung
- Secret-Dateien und Rotation
- Backup, Restore und Restic
- Docker-Cleanup
- RAM-Schutz und Serviceprioritäten

### Abnahme

- Logs aller Custom Services sichtbar
- keine Secrets in Logs
- Backup und Restore erfolgreich
- Teams-Alarm getestet
- RAM-Schutz getestet
- Cleanup schützt aktuelles und vorheriges Release

## Phase 4: Dokumenten- und OCR-Konsolidierung

### Aufgaben

- Document API
- reduzierte OCR Engine
- Kompatibilitätsschicht
- Nutzung alter Endpunkte messen
- n8n-Workflows schrittweise migrieren

### Abnahme

- keine doppelte Fachlogik
- alte Endpunkte leiten intern weiter
- neue API vollständig getestet
- alle produktiven Aufrufer inventarisiert
- Removal frühestens nach zwei Stack-Releases

## Phase 5: Intune-Grundarchitektur

### Aufgaben

- Datenbankschemas
- Tenantmodell
- FastAPI
- Worker
- Jobtabelle
- JWT-Prüfung
- Entra-Apps
- Zertifikate
- Rollenmodell

### Abnahme

- Tenant-Isolation getestet
- API/Worker/Schema kompatibel
- Worker bedarfsgesteuert
- Graph-Authentifizierung erfolgreich
- Rollenfälle vollständig getestet

## Phase 6: Intune-Datenquellen

### Aufgaben

- Settings Catalog
- Device Configurations
- Compliance Policies
- Endpoint Security
- Raw Storage
- Normalisierung und Historie
- Daily Compare und Weekly Full Sync

### Abnahme

- Paging, Throttling und Retry getestet
- Full Sync erfolgreich
- Änderungsvergleich reproduzierbar
- Adapterfehler bleiben isoliert

## Phase 7: Findings und Benachrichtigungen

### Aufgaben

- Regelkern
- Findings
- Ausnahmen
- Reviews und Freigaben
- Teams Workflows
- tägliche Zusammenfassung
- Delivery Status
- Hub-Dashboard

### Abnahme

- Findings reproduzierbar
- Regel- und Normalizer-Version gespeichert
- Ausnahmeablauf getestet
- Teams-Deduplizierung funktioniert
- Critical/High-Alarmierung erfolgreich

## Phase 8: Produktivvorbereitung

### Aufgaben

- Doku konsolidieren
- Betriebshandbuch
- ADRs
- vollständige E2E-Tests
- Restore und Rollback
- technische, Security- und betriebliche Abnahme

### Abnahme

- keine offenen Critical/High-Findings
- alle E2E-Ketten erfolgreich
- Restore, Lösch-Replay und Rollback erfolgreich
- Verantwortlichkeiten benannt
- Go-live-Protokoll vollständig

## Stabilisierungsphase

Nach Go-live mindestens 14 Tage:

- keine neuen Funktionen
- tägliche Prüfung von Logs, Ressourcen, Backups und Findings
- nur Fehlerbehebungen und Security-Updates
- vorheriges Release rollbackfähig halten

Abschluss nur ohne offene Critical/High-Findings, mit erfolgreichen Backups,
Restore-Test, stabilen Ressourcen und formeller Freigabe.
