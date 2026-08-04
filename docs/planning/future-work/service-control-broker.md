# Service-Control-Broker (Zielarchitektur, nicht terminierte Phase)

> Status: dokumentiertes Backlog-Item, **keine Implementierung** in Phase 2A
> oder einer anderen bereits terminierten Phase aus
> `docs/planning/implementation-roadmap.md`. Zugehöriges Finding:
> `docs/planning/security-exceptions/auth-gateway-docker-socket.yml`.

## Ausgangslage

`auth-gateway` mountet `/var/run/docker.sock` und ist über `group_add: ["0"]`
Mitglied der Root-Gruppe, um das Dashboard-Feature "Service Control" zu
ermöglichen. Das ist strukturell root-äquivalent (siehe Finding-Datei für die
vollständige Risikobewertung). Ein vollständiges Feature-Redesign ist kein
Teil dieses oder eines aktuell terminierten PR.

## Zielarchitektur

Ein separater `service-control-broker`-Service:

- besitzt allein den Docker-Socket
- hat keinen externen Caddy-Endpunkt (nur internes Docker-Netz erreichbar)
- akzeptiert ausschließlich authentifizierte interne Aufrufe (z. B. von
  auth-gateway, mit einem separaten internen Service-Secret, nicht dem
  User-JWT)
- verwendet eine feste Service-Allowlist (identisch oder Teilmenge der
  heutigen `_CONTROLLABLE`-Liste)
- erlaubt nur `status`, `start`, `stop`, `restart` und begrenzte Logs
- erlaubt ausdrücklich **kein** `exec`, `create`, `build`, `pull`, `push`,
  `commit`, keine freie Docker-API, keine freien Shell-Kommandos und keine
  frei übergebenen Compose-Argumente
- protokolliert jede Aktion (Audit-Log, analog zur heutigen
  `masterbrain_common.audit`-Integration in auth-gateway)
- läuft non-root, mit `cap_drop: [ALL]`, `no-new-privileges` und
  Read-only-Root-Filesystem, soweit technisch möglich

Optionale Container (`profiles: [optional]`/`[monitoring]`) sollen beim
Deployment bereits erstellt werden, statt zur Laufzeit per
`docker compose up` neu erzeugt zu werden. `docker compose up`, Image-Builds
und Image-Pulls gehören nicht in die Runtime-Service-Control.

Langfristig: Rootless Docker als zusätzliche Härtungsoption separat prüfen —
nicht ungeprüft in eine bestehende Phase integrieren.

## Verbindliche Termine

- **Spätestens 2026-08-15:** GitHub-Issue für den Service-Control-Broker
  anlegen (gemäß `docs/agents/issue-tracker.md`-Konvention), das diese
  Zielarchitektur referenziert.
- **Zieltermin 2026-10-15:** Broker funktionsfähig (mindestens MVP: Start/
  Stop/Restart/Logs über die feste Allowlist, non-root, cap_drop ALL).
- **Spätestens 2026-11-02:** Ausnahmeende laut
  `docs/planning/security-exceptions/auth-gateway-docker-socket.yml`. Ist der
  Broker bis dahin nicht funktionsfähig oder zumindest als terminierter
  Umsetzungs-PR-Plan konkretisiert, muss die Ausnahme dem Repo-Owner zur
  Neubewertung vorgelegt werden — **keine automatische Verlängerung**.
