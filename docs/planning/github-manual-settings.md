# Manuelle GitHub-Repository-Einstellungen (Phase 1)

> Diese Einstellungen können **nicht** durch einen PR/Workflow gesetzt werden —
> sie erfordern Repository-Admin-Rechte im GitHub-UI (oder `gh api` mit einem
> Admin-Token durch einen Menschen). Dieser PR dokumentiert sie nur.
> Reihenfolge beachten: GitHub erlaubt "Require status checks" erst für Checks,
> die mindestens einmal in einem PR erfolgreich gelaufen sind — deshalb zuerst
> diesen PR (oder einen Folge-PR) mit grünen Checks laufen lassen, bevor die
> Checks unten als "Required" markiert werden.

## Branch Protection für `main`

- Require a pull request before merging: **an**
- Require approvals: **mindestens 1**
- Dismiss stale pull request approvals when new commits are pushed: **an**
  (erfüllt "neue Commits setzen Freigaben zurück")
- Require review from Code Owners: **aus, bewusst noch nicht aktivieren**
  (siehe `docs/handbook/09-verantwortlichkeiten.md` — CODEOWNERS ist vorbereitet,
  aber es existiert bislang nur ein Owner; Aktivierung erst nach Einrichtung
  eines zweiten unabhängigen Reviewers/Teams, kein Admin-Bypass als Ersatz)
- Require status checks to pass before merging: **an**, konkrete Pflicht-Checks:
  `lint-yaml`, `compose-config`, `check-image-pinning`, `build-custom-images`,
  `test-presence-check`, `component-tests`, `secret-scan`, `trivy-fs`,
  `validate-exceptions`
- `trivy-image` bewusst **noch nicht** in dieser Liste — siehe eigener
  Abschnitt "trivy-image: bewusst noch kein Required Check" unten.
- Require branches to be up to date before merging: **an**
- Require linear history: **an** (unterstützt Squash-Merge-Pflicht)
- Do not allow bypassing the above settings: **an** (auch für Admins/Owner)
- Restrict who can push to matching branches: **an**, niemand außer über PR-Merge
- Allow force pushes: **aus**
- Allow deletions: **aus**

## Merge-Strategie (Settings → General → Pull Requests)

- "Allow squash merging": **an**
- "Allow merge commits": **aus**
- "Allow rebase merging": **aus**
- Default squash commit message: "Pull request title"

## Code Security and Analysis (Settings → Code security and analysis)

- Secret scanning: **aktivieren** (bei öffentlichen Repos oft bereits Standard —
  explizit prüfen, nicht annehmen)
- Push protection: **aktivieren** (Opt-in-Einstellung, nicht automatisch aktiv)
- Dependabot alerts: **aktivieren**
- Dependabot security updates: **aktivieren**
- Code scanning (SARIF-Anzeige der Trivy-Ergebnisse aus `ci.yml`): sicherstellen,
  dass "Code scanning" nicht durch eine andere Einstellung blockiert wird —
  ein eigener Workflow lädt SARIF hoch, ein GitHub-"Default setup" ist dafür
  nicht zusätzlich nötig

## Workflow-Permissions (Settings → Actions → General)

- Default Workflow-Permissions: **Read repository contents and packages
  permissions only**
- `id-token: write` (für OIDC/Keyless-Signing) **nicht global gewähren** —
  relevant erst, sobald ein Image-Signing-Workflow tatsächlich existiert
  (in Phase 1 bewusst nicht der Fall, siehe Abschnitt "Image-Signing" unten)

## `trivy-image`: bewusst noch kein Required Check

Waehrend der Phase-1-Validierung wurden alle vier Custom Images tatsaechlich
mit Trivy gescannt (`docker build` + `trivy image`, siehe PR-Testprotokoll).
Ergebnis, real und reproduzierbar, ohne jede Ausnahme:

| Image | Critical/High-Findings gesamt |
|---|---|
| `auth-gateway` | 42 (ueberwiegend Debian-12-Basis-Paket-CVEs, u.a. `perl-base`, `zlib1g`, `libsqlite3-0`, plus mitgebundene `docker-ce-cli`-Go-Abhaengigkeiten) |
| `python-nlp-service` | 38 |
| `ocr-service` | 1738 |
| `tts-service` | 1856 |

Das ist **kein Fehler dieses PR** — es ist der reale Ist-Zustand der
bestehenden Base-Images/Abhaengigkeiten (Debian-12-Basis bei den ersten
beiden, EOL-nahes Debian-11/"bullseye" plus grosse ungepinnte ML-Abhaengigkeiten
bei `ocr-service`/`tts-service`, siehe ADR-0008 und
`docs/planning/documentation-inventory.md`). Der `trivy-image`-Job selbst
funktioniert korrekt: Critical/High-Findings sind vollstaendig sichtbar
(siehe Job-Log/SARIF), und ohne eine strukturierte, echt freigegebene
Ausnahme unter `docs/planning/security-exceptions/` blockiert der Check
zurecht (`docs/planning/implementation-roadmap.md`: "Critical und High
blockieren" ist explizit das Ziel).

**Konsequenz fuer Branch Protection:** Wuerde `trivy-image` bereits jetzt als
"Required" markiert, koennte **kein** kuenftiger PR mehr gemergt werden — auch
kein reiner Dokumentations-PR — bis diese Bestandsfunde behoben (Phase 2:
Container haerten, Base-Images aktualisieren/digest-pinnen) oder einzeln
strukturiert und echt freigegeben ausgenommen sind. Deshalb bleibt
`trivy-image` in Phase 1 **aktiv in der CI** (jeder PR sieht die Funde,
SARIF wird hochgeladen), aber **nicht** in der Liste der Required Status
Checks. Das ist eine bewusste, hier dokumentierte Entscheidung, kein
Uebersehen — bitte beim spaeteren Aktivieren von Branch Protection nicht
versehentlich doch als Required markieren, bevor Phase 2 abgeschlossen ist.

## Image-Signing — offener Blocker, kein Workflow in diesem PR

Dieser PR enthält **keinen** `image-signing.yml`-Workflow. Solange folgende
Punkte nicht verbindlich feststehen, ist echtes (oder auch nur vorbereitetes,
aber inaktives) Image-Signing nicht sinnvoll umsetzbar:

1. Ziel-Registry, in die Custom Images (`auth-gateway`, `python-nlp-service`,
   `ocr-service`, `tts-service`) veröffentlicht werden sollen (aktuell: keine —
   Images werden nur lokal/CI-intern gebaut, nicht gepusht).
2. Freischaltung von `id-token: write` für OIDC-Keyless-Signing (Cosign) auf
   Workflow-Ebene, inkl. Prüfung etwaiger Organisationsrichtlinien.
3. Entscheidung, ob Signaturen zusätzlich in eine Transparenz-Log-Instanz
   (z.B. Rekor/Sigstore public good instance) oder eine private Instanz
   geschrieben werden sollen.

Bis diese drei Punkte vom Repo-Owner entschieden sind, bleibt Image-Signing
ausschließlich ein dokumentierter, manueller Blocker — es gibt bewusst keinen
Platzhalter-Workflow mit `if: false`/auskommentierten Schritten, um kein
simuliertes grünes Ergebnis vorzutäuschen.

## Bekannter Blocker: CODEOWNERS mit Einzelowner

Siehe `docs/handbook/09-verantwortlichkeiten.md`. Solange nur `@nic0711` als
Owner bekannt ist, kann "Require review from Code Owners" nicht sinnvoll
aktiviert werden (Self-Approval-Deadlock) und die Freigabe-Matrix für
Critical-Findings (2 unabhängige Freigaben) ist strukturell nicht erfüllbar.
