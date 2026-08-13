# Supabase-Postgres: PG15 → PG17 Upgrade (nicht terminierte Phase)

> Status: dokumentierter, real bestätigter Blocker, **keine Implementierung**
> in diesem oder einem aktuell terminierten PR. Gefunden im Rahmen der
> Bestandsaufnahme für `infra/supabase/` (siehe `docs/29_supabase_migrations.md`).

## Ausgangslage

Die reale, persistente PGDATA (`supabase/docker/volumes/db/data`) ist mit
**PostgreSQL 15** initialisiert (`PG_VERSION` = `15`, real verifiziert
anhand einer isolierten Kopie der Produktions-PGDATA, Original nie
gestartet/verändert). Das im Supabase-Submodule referenzierte Standard-Image
(`supabase/docker/docker-compose.yml`) ist bereits **PostgreSQL 17**
(`supabase/postgres:17.6.1.136`).

**Konsequenz:** Ein normaler `docker compose up` (ohne Override) würde den
`db`-Service nicht starten – real reproduziert:

```
FATAL:  database files are incompatible with server
DETAIL: The data directory was initialized by PostgreSQL version 15, which is not compatible with this version 17.6.
```

## Was Supabase-Upstream dafür bereits mitbringt

Das Supabase-Submodule kennt dieses Szenario bereits offiziell:

- `supabase/docker/docker-compose.pg15.yml` – Override, pinnt
  `supabase/postgres:15.8.1.085` für „bestehende PG15-Installation, noch
  nicht upgegradet". Muss vermutlich aktuell explizit verwendet werden
  (`docker compose -f docker-compose.yml -f docker-compose.pg15.yml up -d`),
  bis der Upgrade durchgeführt ist – **nicht verifiziert, ob das Parent-Repo
  diesen Override aktuell tatsächlich einbindet** (offener Prüfpunkt für die
  Umsetzung dieses Punkts).
- `supabase/docker/utils/upgrade-pg17.sh` – offizielles Upgrade-Skript
  (nutzt Supabase's `pg_upgrade`-Scripts in einem temporären PG15-Container),
  inkl. Backup (`data.bak.pg15`) und dokumentiertem Rollback-Pfad.
- `supabase/docker/tests/test-pg17-upgrade.sh` – zugehöriger Test.

## Warum nicht Teil des SQL-Infrastruktur-PR (`infra/supabase/`)

Zwei unabhängige Themen:

1. **`infra/supabase/migrations/`** (dieser PR): projekteigenes Schema
   versionieren und idempotent/wiederholbar anwendbar machen – funktioniert
   unabhängig von der Postgres-Major-Version.
2. **PG15 → PG17** (dieser Blocker): Server-/Storage-Format-Upgrade der
   gesamten Supabase-Instanz – ein op­erativer Eingriff mit echtem
   Risiko (Downtime, `pg_upgrade`, Rollback-Pfad), der eigene Tests und eine
   eigene, bewusste Freigabe braucht.

Vermischen beider Themen in einem PR würde das Risiko unnötig erhöhen und
die Reviewbarkeit verschlechtern.

## Nächste Schritte (bei Aufnahme in einen künftigen Sprint)

1. Prüfen, ob und wie das Parent-Repo aktuell den `db`-Service tatsächlich
   startet (Override vorhanden? `docker-compose.pg15.yml` bereits implizit
   in Gebrauch?) – bisher nicht verifiziert, da die reale DB in dieser
   Session bewusst nie direkt gestartet wurde.
2. `utils/upgrade-pg17.sh` gegen eine **Kopie** der Produktions-PGDATA
   testen (gleiches Vorgehen wie die Bestandsaufnahme für
   `infra/supabase/migrations/`: physische Kopie, kein Port, Original nie
   anfassen).
3. Downtime-Fenster und Rollback-Test einplanen, bevor die reale PGDATA
   angefasst wird.
4. Nach erfolgreichem Upgrade: `infra/supabase/apply-migrations.sh status`
   erneut prüfen (Migrations-Tracking-Tabelle sollte den Upgrade
   unbeschadet überstehen, da sie ein normales Schema-Objekt ist).
