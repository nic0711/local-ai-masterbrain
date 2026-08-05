# 09 – Verantwortlichkeiten

> Status: Phase-1-Stand — Teil der laufenden Handbuchkonsolidierung
> (siehe `docs/planning/documentation-inventory.md`).

## CODEOWNERS-Zuordnung

Die Datei [`.github/CODEOWNERS`](../../.github/CODEOWNERS) definiert, welche
Pfade eine Owner-Freigabe benötigen. Aktuell ist ausschließlich `@nic0711`
als Platzhalter-Owner für alle geschützten Pfade eingetragen (Repo-Owner laut
`gh repo view`). Das ist ein bekannter, im Abschnitt "Blocker" benannter
struktureller Engpass (siehe unten).

## Freigabe-Matrix für Security-Ausnahmen

Grundlage: `.handoff/claude/architecture/CONTEXT.md` (Abschnitt Security/Release)
und `.github/security-exceptions.template.yml`.

| Schweregrad | Erforderliche Freigaben | Antragsteller darf freigeben? |
|---|---|---|
| Critical | 2 unabhängige Freigaben | Nein |
| High | 1 Freigabe | Nein |

**Wichtig:** Freigaben im Sinne dieser Matrix sind ausschließlich echte
GitHub-PR-Reviews auf den **aktuellen head_sha** des PR. Das lokale
Prüfskript (`scripts/ci/validate-exceptions.py`) prüft nur Struktur, Typ und
Ablaufdatum einer Ausnahmedatei — es trifft keine Aussage darüber, ob sie
freigegeben wurde.

### Korrigiertes Freigabe-Modell (Deadlock behoben)

Eine frühere Version verlangte ein Feld `github_approval_ref` in der
Ausnahmedatei selbst, das erst **nach** einem PR-Review per Commit
eingetragen werden musste. Das erzeugte einen echten Deadlock: unter aktiver
Branch-Protection ("Dismiss stale pull request approvals when new commits
are pushed") setzt jeder neue Commit bestehende Freigaben zurück — also auch
genau der Commit, der die Freigabe-Referenz dokumentiert. Die Freigabe wurde
durch ihre eigene Dokumentation ungültig.

**Korrektur:** `scripts/ci/check-exception-approvals.py` fragt zur Laufzeit
die echten GitHub-PR-Reviews per REST-API ab (`GET /pulls/{n}/reviews`) und
prüft sie gegen den aktuellen `head_sha` — nichts wird in die Ausnahmedatei
zurückgeschrieben, es gibt daher keinen Commit, der eine Freigabe
invalidieren könnte. Ein Review zählt nur, wenn:

- `state == APPROVED`,
- `commit_id` dem aktuellen `head_sha` entspricht (Zusatzschutz, unabhängig
  davon ob Branch-Protection-Stale-Dismissal serverseitig bereits aktiv ist),
- der Reviewer weder PR-Autor noch der in `requested_by` genannten Person
  entspricht.

Das Ergebnis (Liste freigegebener Ausnahme-`id`s) wird als
`approved-exceptions.json`-Artefakt an `trivy-image` weitergereicht.
`scripts/ci/check-trivy-findings.py` wendet eine Ausnahme **nur** an, wenn
ihre `id` in dieser Liste steht — ohne übergebene Datei gilt fail-closed
(keine Ausnahme aktiv), nicht "alles erlaubt".

## Bekannter Blocker: Einzelowner

Mit aktuell nur einem bekannten Repo-Owner (`@nic0711`) ist die Vorgabe
"Critical benötigt zwei Freigaben, Antragsteller darf nicht selbst freigeben"
strukturell nicht erfüllbar — ein Einzelowner kann sich nicht selbst zwei
unabhängige Freigaben erteilen. Dieser Blocker bleibt auch nach dem oben
beschriebenen Deadlock-Fix bestehen: `check-exception-approvals.py` schließt
den PR-Autor korrekt von der Zählung aus, aber automatisierte PRs in diesem
Repo laufen aktuell unter `@nic0711` — identisch mit dem einzigen bekannten
Account. Verifiziert am Beispiel `auth-gateway-docker-socket.yml` (High,
1 Freigabe nötig): 0 qualifizierende Reviews, da kein zweiter Account
existiert, der reviewen könnte. Das ist keine Automatisierungslücke, sondern
ein korrekt sichtbar gemachter Governance-Blocker — er wird erst gelöst,
wenn ein zweiter unabhängiger Reviewer oder ein Team existiert.

Aus demselben Grund bleibt die Branch-Protection-Option "Require review from
Code Owners" in Phase 1 **deaktiviert** (siehe
`docs/planning/github-manual-settings.md`) — sie wird erst aktiviert, wenn ein
zweiter Reviewer/Team existiert. Ein Admin-Bypass ist dafür ausdrücklich
**kein** Ersatz.
