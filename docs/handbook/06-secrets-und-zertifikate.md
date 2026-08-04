# 06 – Secrets und Zertifikate

> Status: Phase-1-Stand — Teil der laufenden Handbuchkonsolidierung
> (siehe `docs/planning/documentation-inventory.md`). Dieses Dokument
> beschreibt das Zielmodell aus ADR-0010 und verweist auf bestehende,
> gültige Dokumentation statt sie zu duplizieren.

## Bezug

- Entscheidungsgrundlage: [`docs/adr/0010-secret-and-certificate-management.md`](../adr/0010-secret-and-certificate-management.md)
- Bestehende, unverändert gültige Sicherheitsdokumentation: [`docs/05_security_hardening.md`](../05_security_hardening.md)

## Zielmodell (laut ADR-0010)

- Runtime-Secrets liegen als rootgeschützte Dateien außerhalb des Repositories
  (Verzeichnisse `0700`, Dateien `0600`), read-only in Container gemountet.
- Keine Secrets in `.env`, Compose-Dateien, Logs oder Backups im Klartext.
- Rotation: 90/180 Tage je nach Secret-Typ, Warnungen bei 60/30/14/7 Tagen
  vor Ablauf.
- Spätere Secret-Provider-Abstraktion (z.B. Vault) ist vorgesehen, aber nicht
  Gegenstand von Phase 1.

## Bestätigung zum Umfang dieses PR

- Dieser PR (`agent/phase-1-governance-ci-supply-chain`) **liest, ändert oder
  erzeugt keine echten Secret-Werte**. `.env`, `dashboard/config.js` und alle
  Backup-Skripte (`backup.sh`, `restore.sh`, `backup/backup*.sh`) bleiben
  unangetastet.
- Für CI-Zwecke (Compose-Config-Validierung) wird ausschließlich eine
  temporäre, nicht-produktive `.env.ci` aus `.env.example` erzeugt und nach
  dem Test wieder gelöscht — niemals committet, niemals mit echten Werten
  befüllt.
- Der neu eingeführte Secret-Scan (`secret-scan`-Job in `.github/workflows/ci.yml`,
  Gitleaks mit `--redact`) prüft den Repository-Inhalt auf versehentlich
  committete Secrets, ohne gefundene Werte im Klartext auszugeben.
- Image-Signing (Cosign, keyless/OIDC) ist in diesem PR **nicht aktiv**
  und benötigt kein Schlüsselmaterial im Repository — siehe
  `docs/planning/github-manual-settings.md`, Abschnitt "Image-Signing" für
  den aktuellen, bewusst offenen Blocker.
