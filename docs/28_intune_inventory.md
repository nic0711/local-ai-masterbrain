# 28 · Intune Geräte-Inventar (Grafana-Dashboard)

## Überblick

Regelmäßig aktualisiertes Geräte-Inventar aus Microsoft Intune (OS-Version,
RAM, CPU-Architektur, primärer Nutzer) als Grafana-Dashboard.

| Baustein | Datei |
|---|---|
| n8n-Sync-Workflow | `n8n-tool-workflows/intune-device-sync.json` |
| Postgres-Tabelle | `infra/supabase/migrations/05_intune_devices.sql` |
| Least-Privilege-Rolle für n8n | `infra/supabase/migrations/06_intune_sync_writer_role.sql` |
| Fehlende Read-Policy für Grafana (Nachtrag zu 05) | `infra/supabase/migrations/07_grafana_intune_reader_select_policy.sql` |
| Grafana-Datasource | `grafana/provisioning/datasources/postgres.yml` |
| Grafana-Dashboard | `grafana/dashboards/intune-device-inventory.json` |

Die Migrationen 05–07 werden über den zentralen Runner
`infra/supabase/apply-migrations.sh` angewendet, nicht über
`docker-entrypoint-initdb.d` – siehe `docs/29_supabase_migrations.md` für
das Gesamtkonzept (Tracking-Tabelle, Baseline-Adoption bestehender
Installationen, Checksum-Schutz).

## Warum kein Teil des Intune Policy Hub

`CONTEXT.md` beschreibt bereits eine vollständige Zielarchitektur „Intune
Policy Hub" (ADR-0001–0005: FastAPI + Worker + Postgres-Jobqueue +
zertifikatsbasierte, mandantenfähige Entra-Apps). ADR-0001 legt fest, dass
diese Entwicklung erst **nach** Abschluss der Stack-Härtung (Phasen 1–4)
beginnen soll. Dieses Inventar ist bewusst **kein** Teil davon – kein
`intune_raw`/`intune_core`-Schema, kein FastAPI/Worker, keine
mandantenfähige Zertifikats-Auth, sondern ein schlanker, eigenständiger
n8n-Workflow mit Client-Secret-Auth gegen einen einzelnen Tenant. Es kann
später bei Bedarf durch die echte Phase-5/6-Architektur ersetzt werden, ohne
dass etwas Bestehendes davon abhängt.

## Datengrenze bei CPU

Microsoft Graph liefert im stabilen `v1.0`-Endpoint
`/deviceManagement/managedDevices` keine CPU-Modelldaten, nur
`processorArchitecture` (x64/arm64/x86). Der Beta-Endpoint
`deviceHardwareData` hätte mehr Details, bräuchte aber einen Call pro Gerät
(nicht in der Listenabfrage enthalten) und ist als Beta-API nicht
stabilitätsgarantiert – bewusst nicht verwendet. Die Spalte
„CPU-Architektur" im Dashboard zeigt also nur die Architektur, kein
Prozessormodell. Das ist keine unvollständige Implementierung, sondern die
Grenze des verwendeten stabilen Endpunkts.

## 1. Entra-ID-App-Registrierung (externer, manueller Schritt)

Kann nicht automatisiert werden – muss im Azure Portal von einem
Tenant-Admin ausgeführt werden.

1. [Azure Portal](https://portal.azure.com) → **App-Registrierungen** →
   Neue Registrierung
   - Name: `brain-local-intune-inventory`
   - Unterstützte Kontotypen: *Nur Konten in diesem Organisationsverzeichnis*
2. **API-Berechtigungen** → Berechtigung hinzufügen → Microsoft Graph →
   **Anwendungsberechtigungen** → `DeviceManagementManagedDevices.Read.All`
3. **Admin-Zustimmung erteilen** für den Tenant (Button in derselben Ansicht)
4. **Zertifikate und Geheimnisse** → Neuer geheimer Clientschlüssel → Wert
   sofort kopieren (wird nur einmal angezeigt)
5. Notieren: `Application (client) ID`, `Client Secret`, `Directory (tenant) ID`

## 2. Migrationen anwenden

Voraussetzung: `docker compose up -d db` läuft bereits. Details/Sicherheits-
garantien zum Runner: `docs/29_supabase_migrations.md`.

Zuerst den Ist-Zustand prüfen:

```bash
infra/supabase/apply-migrations.sh status
```

- **Bestehende Installation** (01–04 bereits als Baseline übernommen, siehe
  `docs/29_supabase_migrations.md`): einfach

  ```bash
  infra/supabase/apply-migrations.sh apply
  ```

  Das wendet **nur** die noch nicht getrackten Migrationen an – bei einer
  bereits baselinierten Installation sind das genau `05_intune_devices.sql`,
  `06_intune_sync_writer_role.sql` und
  `07_grafana_intune_reader_select_policy.sql`, jeweils **einmal**,
  transaktional. 01–04 werden dabei nicht erneut ausgeführt (Checksum-
  Vergleich gegen die Tracking-Tabelle).
- **Frische Installation** (Tracking-Tabelle noch leer): derselbe Befehl
  wendet alle sieben Migrationen 01–07 der Reihe nach an.

**Nicht** manuell `psql -f infra/supabase/migrations/05_intune_devices.sql`
o.ä. ausführen – das umgeht das Migrations-Tracking und kann bei einem
späteren `apply` zu einem Checksum-Konflikt führen (Runner bricht dann
bewusst hart ab, siehe `docs/29_supabase_migrations.md`).

Danach prüfen, ob Tabelle und Rollen angelegt wurden:

```bash
docker compose exec db psql -U postgres -d postgres -c "\dt public.intune_devices"
docker compose exec db psql -U postgres -d postgres -c "\du grafana_intune_reader"
docker compose exec db psql -U postgres -d postgres -c "\du intune_sync_writer"
```

Mit Schritt 3 (n8n-Rolle) fortfahren.

## 3. Least-Privilege-Rolle für n8n anlegen (manueller Schritt)

Der Sync-Workflow führt ausschließlich ein `INSERT ... ON CONFLICT
(intune_device_id) DO UPDATE` gegen `public.intune_devices` aus (kein
DELETE). Dafür existiert die dedizierte Rolle `intune_sync_writer` mit
`SELECT`/`INSERT`/`UPDATE` auf genau dieser einen Tabelle – **nicht** der
`postgres`-Superuser. Das `SELECT` ist kein Versehen: unter Row Level
Security benötigt `ON CONFLICT DO UPDATE` nachweislich (real gegen eine
disposable PostgreSQL-15-Instanz verifiziert) auch bei einem reinen
`EXCLUDED`-basierten `SET` zusätzlich `SELECT`, damit Postgres die
Sichtbarkeit einer eventuell bereits vorhandenen Zeile für die aufrufende
Rolle prüfen kann – siehe Begründung in
`infra/supabase/migrations/06_intune_sync_writer_role.sql`. Kein `DELETE`,
kein `CREATE`, keine anderen Tabellen.

Die Rolle wird durch Migration 06 automatisch angelegt, aber bewusst
**ohne** Passwort (`NOLOGIN`), damit kein Secret im Git-Verlauf landet.
Passwort einmalig manuell setzen (`WITH LOGIN` hebt `NOLOGIN` auf, **nicht**
nur `PASSWORD` setzen – sonst bleibt die Rolle login-gesperrt):

```bash
docker compose exec db psql -U postgres -c \
  "ALTER ROLE intune_sync_writer WITH LOGIN PASSWORD '<frei gewaehltes Passwort>';"
```

Das Passwort wird **nicht** in `.env` benötigt (nur Grafana liest sein
Passwort aus `.env` via `$__env{}` – n8n-Credentials werden über die
n8n-UI verwaltet, siehe Schritt 4).

## 4. n8n einrichten

1. **Workflow importieren**: n8n → Workflows → Importieren →
   `intune-device-sync.json`
2. **Postgres-Credential** im Knoten „Upsert intune_devices" anlegen: Host
   `db`, Port `5432`, DB `postgres`, User **`intune_sync_writer`**, Passwort
   = der in Schritt 3 gesetzte Wert. **Nicht** `postgres` verwenden – dieser
   Workflow braucht ausschließlich Insert/Update auf einer Tabelle, kein
   Superuser-Zugriff.
3. **Variablen** setzen (n8n → Settings → Variables):
   ```
   AZURE_TENANT_ID    = <Directory (tenant) ID>
   INTUNE_CLIENT_ID   = <Application (client) ID>
   INTUNE_CLIENT_SECRET = <Client Secret>
   ```
4. Workflow aktivieren → läuft täglich 06:00, Pagination über
   `@odata.nextLink` ist im HTTP-Node bereits konfiguriert

## 5. Least-Privilege-Rolle für Grafana anlegen (manueller Schritt)

Die Tabelle `public.intune_devices` und die Rolle `grafana_intune_reader`
werden durch Migration 05 angelegt – die Rolle hat aber bewusst **kein**
Passwort (`NOLOGIN`), damit kein Secret im Git-Verlauf landet. Passwort
einmalig manuell setzen (`WITH LOGIN` hebt `NOLOGIN` auf, **nicht** nur
`PASSWORD` setzen):

```bash
docker compose exec db psql -U postgres -c \
  "ALTER ROLE grafana_intune_reader WITH LOGIN PASSWORD '<gleicher-wert-wie-.env>';"
```

Danach in `.env`:

```
GRAFANA_PG_PASSWORD=<gleicher-wert-wie-oben>
```

Grafana neu starten: `docker compose restart grafana`. Danach in Grafana →
Connections → Data sources → „Intune Devices (Postgres)" → **Save & Test**
prüfen.

**Warum keine Superuser-Credentials für Grafana:** `GF_USERS_AUTO_ASSIGN_ORG_ROLE=Admin`
gibt jedem eingeloggten Nutzer Grafana-Org-Admin-Rechte, d.h. Zugriff auf
Explore mit beliebigen SQL-Abfragen gegen jede konfigurierte Datasource.
Mit dem `postgres`-Superuser wäre das ein voller DB-Zugriff für jeden
Grafana-Nutzer. `grafana_intune_reader` hat nur `SELECT` auf
`public.intune_devices`.

## 6. Dashboard

Wird per Grafana-Provisioning automatisch geladen (`grafana/dashboards/`,
alle 60s neu eingelesen) – kein manueller Import nötig. Zu finden unter
„Intune Geräte-Inventar": Gesamtzahl Geräte, Verteilung nach OS-Version,
Verteilung nach Compliance-Status, vollständige Inventar-Tabelle.

## Troubleshooting

**Sync-Workflow schlägt mit 401 fehl:**
- `INTUNE_CLIENT_ID`/`INTUNE_CLIENT_SECRET`/`AZURE_TENANT_ID` in den
  n8n-Variablen prüfen
- Admin-Zustimmung für `DeviceManagementManagedDevices.Read.All` erteilt?

**Sync-Workflow schlägt mit einem Postgres-Permission-Fehler fehl:**
- Läuft das n8n-Postgres-Credential wirklich als `intune_sync_writer`
  (nicht mehr `postgres`)?
- `intune_sync_writer` hat bewusst nur `SELECT`/`INSERT`/`UPDATE` auf
  `public.intune_devices` (kein `DELETE`, keine anderen Tabellen) – falls
  der Fehler auf ein anderes fehlendes Recht hindeutet, zuerst die
  tatsächlich ausgeführte Query im n8n-Execution-Log prüfen, bevor
  zusätzliche Rechte vergeben werden (siehe Kommentar in
  `06_intune_sync_writer_role.sql`)

**Grafana-Datasource „Save & Test" schlägt fehl:**
- Passwort in `.env` (`GRAFANA_PG_PASSWORD`) und in der DB
  (`ALTER ROLE grafana_intune_reader ...`) identisch?
- `docker compose restart grafana` nach Änderung an `.env` ausgeführt?

**Tabelle bleibt leer:**
- Workflow in n8n aktiv und mindestens einmal manuell ausgeführt?
- `docker compose logs n8n | tail -50` auf Fehler im Sync-Lauf prüfen
- `infra/supabase/apply-migrations.sh status` prüfen – sind 05, 06 und 07
  wirklich angewendet (nicht nur `baseline`)?

**Dashboard zeigt „Geräte gesamt: 0" oder leere Tabelle, obwohl der
Sync-Workflow erfolgreich lief:**
- `infra/supabase/apply-migrations.sh status` prüfen – ist
  `07_grafana_intune_reader_select_policy.sql` angewendet? Ohne diese
  Migration liefert `grafana_intune_reader` wegen fehlender RLS-Policy
  still `0 rows`, ohne Fehlermeldung (siehe Kommentar in der Migration)
