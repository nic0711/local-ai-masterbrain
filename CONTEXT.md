# CONTEXT.md

## Status

Verbindliche Zielarchitektur für die Konsolidierung und Absicherung des gesamten
`local-ai-masterbrain`-Stacks sowie für die anschließende Entwicklung des
Intune Policy Hub.

Stand: 2026-08-03

## Ziel

1. Den bestehenden Stack reproduzierbar, sicher, testbar und wartbar machen.
2. Danach den Intune Policy Hub auf dieser stabilisierten Basis entwickeln.
3. Eine zentrale konsistente Dokumentation plus ADR-Archiv aufbauen.

## Betriebsmodell

- Self-hosted Docker Compose
- Ein produktiver Host
- Kein Kubernetes
- Integration in den bestehenden Stack
- Technisch mandantenfähig, im MVP ein produktiver Tenant
- Manuelle Produktionsfreigabe
- Monatliches geprüftes Stack-Release
- Security-Hotfixes unabhängig vom Monatsrhythmus

## Zielkomponenten

```text
services/
├── platform/
│   ├── auth-gateway/
│   └── intune-policy-service/
├── document/
│   ├── document-api/
│   └── ocr-engine/
└── media/
    └── tts-service/

frontend/
└── intune-policy-web/

packages/python/
└── masterbrain-common/
```

Die Migration darf schrittweise erfolgen. Bestehende Pfade müssen nicht sofort
umbenannt werden.

## Verbindliche Architekturentscheidungen

### Container

- Custom Container bleiben getrennt.
- Kein Universal-Container.
- Gemeinsame Standards und wenige Base-Image-Familien.
- `document-api` übernimmt PDF-Annahme, Extraktion, NER, OCR-Auswahl und
  Ergebnisnormalisierung.
- `ocr-engine` übernimmt nur die eigentliche OCR-Ausführung.
- `tts-service` bleibt wegen abweichender ML-, Audio-, Video- und
  Ressourcenanforderungen separat.
- `auth-gateway` bleibt strikt getrennt und erhält keine Fachlogik.

### Base-Image-Familien

```text
masterbrain/python-runtime
masterbrain/python-ml-cpu
masterbrain/node-build
masterbrain/nginx-runtime
```

Alle Images werden exakt per Version und Digest gepinnt, gescannt, mit SBOM
versehen und signiert.

### Mindeststandard je Custom Container

- Non-root
- feste UID/GID
- reproduzierbare Lockfiles
- keine offenen Versionsbereiche in Produktion
- Multi-Stage-Build, soweit sinnvoll
- keine Build-Werkzeuge im Runtime-Image
- `cap_drop: ALL`, soweit möglich
- Read-only Root Filesystem, soweit möglich
- CPU- und RAM-Limits
- Health-, Ready- und Metrics-Endpunkt
- strukturierte JSON-Logs
- Unit-, API-, Integrations- und Container-Smoke-Tests
- eigene SemVer-Version
- `/version`-Endpoint
- Trivy-Scan, SBOM und Signatur

### Gemeinsames Python-Paket

`masterbrain-common` ist ein intern versioniertes Wheel mit eigener SemVer-Version.

Zulässig:

- Konfiguration
- Logging
- Correlation IDs
- Health/Ready/Metrics
- JWT-Prüfung
- Fehlerformate
- Secret-Datei-Lader
- technische Audit-Helfer

Nicht zulässig:

- Intune-Fachlogik
- OCR-/TTS-Logik
- ML-Abhängigkeiten
- servicebezogene Geschäftsmodelle

Jeder Service pinnt eine konkrete Version.

## Intune Policy Hub

### Technologie

- FastAPI
- React/Vite
- nginx
- bestehendes Supabase/PostgreSQL
- PostgreSQL-Jobtabelle
- separater Worker
- n8n nur für Zeitplanung, Start und Benachrichtigung

### Datenbankschemas

```text
intune_raw
intune_core
intune_analysis
intune_api
```

Jede Business-Tabelle enthält `tenant_id`.

Browserzugriffe erfolgen ausschließlich über FastAPI, freigegebene Views,
RPC-Funktionen und RLS.

### MVP-Datenquellen

- Settings Catalog
- klassische Device Configurations
- Compliance Policies
- Endpoint Security

Weitere Quellen werden als code-definierte Adapter ergänzt.

### Synchronisation

- Änderungsvergleich täglich
- Full Sync wöchentlich
- manuell jederzeit
- keine generische Delta-Annahme
- Vergleich über Metadaten, normalisierte Hashes und vollständige Validierung

### Worker

- gleiches Image wie API, anderer Startbefehl
- bedarfsgesteuerter Start
- Standard-Idle-Timeout 600 Sekunden
- laufende Jobs werden nie durch Idle-Timeout beendet
- maximal ein Full Sync pro Tenant
- transaktionale Reservation
- Heartbeat und Reclaim
- keine parallelen Doppeljobs

### Authentifizierung

Browser zu FastAPI:

- Supabase JWT
- Signatur, Ablauf, Issuer, Audience, Benutzer, Rolle und Tenant selbst prüfen
- Proxy-Header nicht als alleinige Identität akzeptieren

n8n zu FastAPI:

- kurzlebige asymmetrisch signierte JWTs
- maximal fünf Minuten
- Issuer, Audience, `jti`, Scopes
- keine Tokens in Logs

Graph:

- getrennte Entra-Apps für Intune Policy Reader und Directory Reader
- Zertifikate statt Client Secrets
- eigene Zertifikate pro App

### Rollen

- Viewer
- Analyst
- Policy Owner
- Hub Administrator
- Security Approver
- Documentation Owner

Entra-Gruppen sind Standardquelle. Ein expliziter manueller Deny hat Vorrang.

## Findings und Regeln

- deterministischer Regelkern in Python
- keine KI-Entscheidungen im MVP
- Regelparameter, Severity, Aktivierung, Review und Ausnahmen in DB/UI
- Finding speichert Regelversion, Normalizer-Version, Parameter, Zeit,
  Objekt-IDs und Evidence
- relevante Änderungen erzeugen Findings
- normale Änderungen bleiben Versionshistorie

### Ausnahmen

Ausnahmen können Policy, Setting, Zielgruppe, Wertkombination oder Finding-Muster
betreffen.

Pflichtfelder:

- Grund
- Owner
- Ersteller
- Scope
- Kompensationsmaßnahme
- Beginn
- Ablauf oder unbefristet
- Status
- Auditverlauf

Unbefristete Ausnahmen werden alle 180 Tage geprüft.

## Security und Releases

### Scanner

- Trivy für Repository, Images, IaC, Secrets und SBOM
- GitHub Secret Scanning
- Push Protection
- SARIF-Upload
- CycloneDX-SBOM

Critical und High blockieren Releases.

### Security-Ausnahmen

- Critical: zwei Freigaben
- High: eine Freigabe
- Antragsteller darf nicht selbst freigeben
- mindestens ein Security Approver oder Hub Administrator
- Begründung, Risiko, Kompensationsmaßnahme, Owner und Ablaufdatum

### GitHub-Governance

- keine direkten Commits auf `main`
- nur Pull Requests
- Squash-Merge
- Pflicht-CI
- mindestens eine unabhängige Freigabe
- sensible Pfade über CODEOWNERS und zwei Freigaben
- neue Commits setzen Freigaben zurück
- keine Force-Pushes

### Release-Modell

- eigene SemVer je Komponente
- separate DB-Schemaversionen
- Ruleset- und Normalizer-Version
- zusätzlich geprüftes Gesamt-Stack-Release
- Release-Manifest mit Versionen, Digests, SBOM, Signaturen und Kompatibilität
- externe Images mit echter Upstream-Version und Digest
- kein `latest` in Produktion

### Updates

- tägliche Update- und CVE-Prüfung
- automatisierte Update-PRs
- Critical/High möglichst innerhalb 24 Stunden
- normale Dependencies mindestens wöchentlich
- n8n Minor mindestens wöchentlich gebündelt
- Major separat
- keine Beta-/Pre-Releases
- alle Custom Images wöchentlich vollständig ohne Cache neu bauen
- Wochenbuild erzeugt Release-Kandidaten, kein Auto-Deployment

## Secrets

- außerhalb des Repositories
- Verzeichnisse `0700`
- Dateien `0600`
- read-only Mount
- nur in berechtigte Container
- keine Secrets in `.env`, Compose, Logs oder Backups
- spätere Secret-Provider-Schnittstelle für Vault möglich

Rotation:

- Service-JWT-Schlüssel 90 Tage
- Webhooks/API-Tokens 180 Tage
- Zertifikate vor Ablauf
- sofort bei Verdacht, Leak oder Mitarbeiterwechsel
- Warnungen 60/30/14/7 Tage

## Logging und Monitoring

- zentrale strukturierte JSON-Logs
- einheitliches Schema über `masterbrain-common`
- Correlation ID über API, Worker und n8n
- keine Tokens, Schlüssel, Webhooks oder unnötigen Personendaten

Aufbewahrung:

- Standard 30 Tage
- Security/Audit/Release 180 Tage

Alarmierung:

- Critical/High sofort per Teams
- Medium täglich
- Low/Info Dashboard
- Teams Workflows statt klassischer Incoming Webhooks
- E-Mail erst nach vorhandenem SMTP-Relay

## Ressourcen

Priorität:

1. Auth, Caddy, Supabase, Monitoring
2. Dashboard, n8n, Intune API
3. Worker und Document API
4. OCR, TTS und optionale ML-Dienste

Speicherdruck:

- ab 80 % keine neuen ML-Jobs
- ab 90 % optionale Dienste kontrolliert stoppen
- unter 70 % Neustart wieder zulässig
- Hysterese
- wiederholter Druck erzeugt High-Finding

## Datenaufbewahrung

Standard:

- temporäre Uploads 24 Stunden
- OCR/TTS-Artefakte 30 Tage
- Intune-Rohdaten 90 Tage
- Standardlogs 30 Tage
- Security/Audit/Release 180 Tage
- normalisierte Historie und Findings dauerhaft, sofern Tenant nichts anderes vorgibt

Personenbezogene Löschung erfolgt über zentralen Löschauftrag mit Vorschau,
Freigabe, Ausführung, Verifikation und Audit.

Backups werden nicht verändert. Nach Restore wird ein dauerhaftes Löschregister
erneut angewendet.

## Backup und Restore

- tägliches Backup
- Restic
- S3-kompatibel und SFTP
- lokal 14 Tage
- Offsite 30 tägliche und 12 monatliche
- RPO 24 Stunden
- RTO 4 Stunden
- monatlicher isolierter DB-Restore-Test
- halbjährlicher vollständiger Stack-Wiederanlauf
- RTO-Überschreitung ist High-Finding

Backup-Artefakte:

```text
supabase-full-YYYYMMDD.dump
intune-schemas-YYYYMMDD.dump
intune-config-YYYYMMDD.json
backup-manifest-YYYYMMDD.json
```

Keine privaten Schlüssel, Tokens oder unverschlüsselten Webhooks.

## Docker-Cleanup

Wöchentlich sicher bereinigen:

- gestoppte Container älter 168 Stunden
- ungenutzte Images älter 168 Stunden
- ungenutzte Netzwerke
- Buildcache älter 168 Stunden
- Zielgröße Buildcache 10 GB

Nie automatisch:

- `docker volume prune`
- `docker system prune --volumes`

Aktuelles und vorheriges Release werden über Image-IDs/Digests aus gültigen
Release-Manifesten geschützt.

## Tests

- Unit
- API
- Integration
- Container-Smoke
- kritische Module mindestens 80 % Coverage
- gezielte Risiko- und Fehlerfalltests bleiben Pflicht

E2E-Ketten:

- Login → Rollen → Dashboard
- Intune Sync → Analyse → Finding → Teams
- Dokument → OCR → Ergebnis → Löschung
- Backup → Restore → Lösch-Replay → Health
- Service-Start → Job → kontrolliertes Stoppen

## Dokumentation

Ziel:

```text
README.md
CONTEXT.md
docs/
├── handbook/
└── adr/
```

Bestehende Dokumentation wird inventarisiert, übernommen, bereinigt und ersetzt.
Es darf am Ende keine parallelen scheinbar gültigen Altanleitungen geben.

Technische Änderung und Dokumentation gehören in denselben PR.

## Phasen

1. Governance und CI
2. Custom Container härten
3. Betrieb vereinheitlichen
4. Document/OCR konsolidieren
5. Intune-Grundarchitektur
6. Intune-Datenquellen
7. Analyse, Findings und Benachrichtigung
8. Produktivvorbereitung

Jede Phase besitzt messbare Abnahmekriterien und unabhängige Freigaben.

## Go-live

Pflicht:

- technische Abnahme
- Security-Abnahme
- betriebliche Abnahme
- keine offenen Critical/High-Findings
- Restore und Rollback erfolgreich
- Dokumentation vollständig
- Alarmierung funktionsfähig

Danach mindestens 14 Tage Stabilisierungsphase ohne neue Funktionen.

Die Phase endet nur bei stabilen Messwerten, erfolgreichen Backups,
erfolgreichem Restore-Test und ohne offene Critical/High-Findings.
