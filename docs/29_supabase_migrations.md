# 29 · Supabase-Migrationen (projekteigenes Schema)

## Überblick

Projektspezifische Datenbank-Migrationen (RAG-Pipeline, OCR-Ergebnisse,
System-Tabellen, Intune-Geräte-Inventar) liegen unter
`infra/supabase/migrations/` – im Parent-Repo versioniert, **nicht** im
Supabase-Submodule (`supabase/`, zeigt auf `supabase/supabase.git`, eigene
Governance, falscher Ort für projekteigenes Schema).

| Datei | Inhalt |
|---|---|
| `01_shared_functions.sql` | `update_updated_at_column()` – zentral, einmalig |
| `02_rag_schema.sql` | RAG-Pipeline-Tabellen (documents, chunks, sessions, …) |
| `03_ocr_results.sql` | OCR-Ergebnistabelle (TrOCR/Tesseract) |
| `04_complete_system_tables.sql` | User-Profile, Files, Workflows, Monitoring, AI, Neo4j, Notifications |
| `05_intune_devices.sql` | Intune-Geräte-Inventar (siehe `docs/28_intune_inventory.md`) |
| `apply-migrations.sh` | Runner (siehe unten) |

## Warum kein `docker-entrypoint-initdb.d`

Der `db`-Service im Supabase-Submodule
(`supabase/docker/docker-compose.yml`) mountet nur die Supabase-eigenen
Init-Skripte (`roles.sql`, `jwt.sql`, …) nach `/docker-entrypoint-initdb.d/`
– dieser Mechanismus läuft ohnehin nur **einmalig beim allerersten Start
eines leeren Volumes**. Die reale Installation hat aber bereits
Bestandsdaten (verifiziert: `02`–`04` liefen früher schon einmal manuell
gegen die Produktions-DB). Ein Init-Skript-Ansatz könnte diese Migrationen
nie rückwirkend auf eine bestehende Installation anwenden. Deshalb: ein
echtes, nachvollziehbares **Migrationsmodell** mit Tracking-Tabelle und
explizitem Runner statt automatischem Hook.

## Tracking-Tabelle

`apply-migrations.sh` legt bei Bedarf `public._project_migrations` an:

| Spalte | Bedeutung |
|---|---|
| `version` | Datei-Präfix, z. B. `02` (Primary Key) |
| `name` | Rest des Dateinamens, z. B. `rag_schema` |
| `checksum` | SHA-256 des Dateiinhalts zum Zeitpunkt der Anwendung |
| `applied_at` | Zeitstempel |
| `baseline` | `true` = als bereits vorhandener Zustand übernommen, nicht ausgeführt; `false` = tatsächlich angewendet |

Bewusst **nicht** `auth.schema_migrations` wiederverwendet – das ist
Supabase-intern (eigene Auth-Migrationen), Namenskollision/
Verantwortungsvermischung sonst.

## Nutzung

Voraussetzung: `docker compose up -d db` läuft bereits.

### Normale Anwendung (neue/leere Installation)

```bash
infra/supabase/apply-migrations.sh apply
```

Wendet alle noch nicht getrackten Dateien in Reihenfolge an – jede Datei in
einer eigenen Transaktion (`psql -1 -v ON_ERROR_STOP=1`), inklusive
Tracking-Eintrag. Schlägt ein Statement fehl, wird die gesamte Datei
zurückgerollt, das Skript bricht mit Exit-Code ≠ 0 ab (kein stiller Erfolg
trotz Fehler mehr).

### Bestehende, bereits initialisierte Installation

Bei einer Installation, die `02`–`04` bereits (z. B. manuell) angewendet
hat, **nicht** blind erneut ausführen (nicht alle Statements darin sind
idempotent genug für einen echten Doppellauf gegen unabhängig entstandene
Bestandsdaten). Stattdessen den bestehenden Zustand kontrolliert als
Baseline übernehmen:

```bash
infra/supabase/apply-migrations.sh baseline \
  01_shared_functions.sql 02_rag_schema.sql 03_ocr_results.sql 04_complete_system_tables.sql
infra/supabase/apply-migrations.sh apply   # wendet nur noch 05 (neu) an
```

`baseline` führt den SQL-Inhalt **nicht** aus, sondern trägt nur einen
Tracking-Eintrag mit `baseline = true` ein – eine bewusste, vom Betreiber
zu verantwortende Aussage („dieser Zustand existiert bereits so"), keine
automatische Prüfung.

### Status

```bash
infra/supabase/apply-migrations.sh status
```

## Sicherheitsgarantien

- `ON_ERROR_STOP=1` immer aktiv – ein fehlschlagendes Statement beendet den
  Lauf mit Fehler, nicht mit stillschweigend übersprungener Zeile.
- `psql -1` (Single-Transaction) – jede Migrationsdatei läuft atomar: ganz
  oder gar nicht.
- Checksummen-Vergleich verhindert, dass eine bereits angewendete Migration
  unbemerkt mit geändertem Inhalt erneut läuft – bei Abweichung bricht das
  Skript hart ab, Änderungen brauchen eine neue Datei mit neuer
  Versionsnummer.
- Kein automatischer Hook – der Betreiber entscheidet bewusst, wann er den
  Runner aufruft (analog zu anderen bereits etablierten manuellen Schritten
  wie der Entra-App-Registrierung oder dem Grafana-Rollen-Passwort).

## Alte, verwaiste Dateien

`supabase/docker/volumes/db/init/02_rag_schema.sql` bis `05_intune_devices.sql`
(innerhalb des Supabase-Submodule-Pfads) sind durch diese Migration
**ersetzt**. Sie waren nie von Git getrackt (weder Submodule noch
Parent-Repo) und werden vom `db`-Service auch nicht gemountet – funktional
bereits inert. Sie können lokal gefahrlos gelöscht werden, lassen sich aber
nicht per Commit „entfernen", da sie nie versioniert waren.

## Bekannter, separater Blocker: PostgreSQL 15 → 17

Die reale PGDATA ist mit PostgreSQL 15 initialisiert, das im Submodule
referenzierte Image ist bereits PostgreSQL 17 – inkompatibel. Betrifft den
gesamten Datenbank-Betrieb, nicht nur diese Migrationen, und wird **nicht**
im Rahmen dieses Infra-PR behoben. Details:
`docs/planning/pg15-to-pg17-upgrade-blocker.md`.
