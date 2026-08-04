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
GitHub-PR-Reviews auf die jeweilige Ausnahmedatei unter
`docs/planning/security-exceptions/`, durchgesetzt über Branch-Schutzregeln
und CODEOWNERS. Eine in einer YAML-Datei eingetragene `approvals`-Liste ist
**keine** gültige Freigabe — das lokale Prüfskript
(`scripts/ci/validate-exceptions.py`) prüft nur Struktur, Ablaufdatum, Scope
und Konsistenz einer Ausnahme, niemals ob sie tatsächlich freigegeben wurde.

## Bekannter Blocker: Einzelowner

Mit aktuell nur einem bekannten Repo-Owner (`@nic0711`) ist die Vorgabe
"Critical benötigt zwei Freigaben, Antragsteller darf nicht selbst freigeben"
strukturell nicht erfüllbar — ein Einzelowner kann sich nicht selbst zwei
unabhängige Freigaben erteilen. Dieser PR löst das nicht auf (kein Anlegen
von Platzhalter-Accounts), sondern benennt es als offenen, manuell zu klärenden
Punkt: Es wird ein zweiter unabhängiger Reviewer oder ein Team benötigt, bevor
Critical-Ausnahmen nach dieser Matrix tatsächlich freigegeben werden können.

Aus demselben Grund bleibt die Branch-Protection-Option "Require review from
Code Owners" in Phase 1 **deaktiviert** (siehe
`docs/planning/github-manual-settings.md`) — sie wird erst aktiviert, wenn ein
zweiter Reviewer/Team existiert. Ein Admin-Bypass ist dafür ausdrücklich
**kein** Ersatz.
