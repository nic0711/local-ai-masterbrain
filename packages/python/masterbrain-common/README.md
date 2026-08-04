# masterbrain-common

Intern versioniertes Wheel mit eigener SemVer-Version (aktuell `0.1.0`), siehe
`CONTEXT.md` (Abschnitt "Gemeinsames Python-Paket") und ADR-0008.

## Scope in dieser Version (Phase 2A)

Bewusst eng geschnitten auf tatsaechlich verwendete und getestete Funktionen.
Von den 8 in `CONTEXT.md` grundsaetzlich erlaubten Kategorien sind in dieser
Version enthalten:

- **JWT-Pruefung** (`masterbrain_common.jwt_verify`) — HS256-Verifikation mit
  TTL-Cache und RFC-7515-`crit`-Header-Ablehnung, migriert aus
  `auth-gateway/app.py`.
- **Logging / Correlation-ID** (`masterbrain_common.logging`) — JSON-Logging
  via `python-json-logger`, request-scoped Correlation-ID ueber `contextvars`.
- **Health/Ready** (`masterbrain_common.health`) — Response-Helper fuer
  `/health` (leichtgewichtig, keine externen Abhaengigkeiten) und `/ready`
  (prueft externe Abhaengigkeiten; **niemals** als Docker-`HEALTHCHECK`-Ziel
  verwenden, da das zu Restart-Schleifen bei kurzzeitig nicht erreichbaren
  Abhaengigkeiten fuehren wuerde).
- **Fehlerformat** (`masterbrain_common.errors`) — einheitliches Error-JSON.
- **Audit-Helfer** (`masterbrain_common.audit`) — strukturierte
  Audit-Log-Events fuer sicherheitsrelevante Aktionen.

**Nicht enthalten** (bewusst, um spekulativen/ungenutzten Code zu vermeiden):
`config.py` (generischer Config-Loader), `secrets.py` (Datei-basierter
Secret-Loader), `/metrics` (Prometheus-Endpoint). Diese kommen erst, wenn ein
konkreter Verwendungszweck in einer spaeteren Phase entsteht.

**Ausdruecklich nicht zulaessig** (laut `CONTEXT.md`, gilt dauerhaft): Intune-
Fachlogik, OCR-/TTS-Logik, ML-Abhaengigkeiten, servicebezogene
Geschaeftsmodelle. Die Supabase-spezifische Fallback-Verifikation von
`auth-gateway` (wenn `JWT_SECRET` nicht gesetzt ist) bleibt deshalb bewusst
*im Service selbst*, nicht in diesem Paket — `jwt_verify` haengt nicht vom
`supabase`-SDK ab.

## Verwendung

Jeder Service pinnt eine konkrete Version (aktuell `masterbrain-common==0.1.0`)
und installiert das Paket als Wheel (`pip install --no-deps <wheel>`), nicht
per `pip install -e`. Siehe `auth-gateway/Dockerfile` fuer das
Referenz-Build-Pattern.
