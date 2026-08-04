# Gitleaks-Baseline (Bestandsfindings)

`docs/planning/gitleaks-baseline.json` ist eine maschinell erzeugte Baseline
(`gitleaks detect --no-git --report-format json`) der im **aktuellen
Dateiinhalt** (Checkout-Zustand, nicht Git-Historie) vorhandenen Findings.
Erzeugt mit:

```bash
docker run --rm -v "$PWD":/repo \
  zricethezav/gitleaks@sha256:c00b6bd0aeb3071cbcb79009cb16a60dd9e0a7c60e2be9ab65d25e6bc8abbb7f \
  detect --source=/repo --no-git --report-format json --report-path /repo/docs/planning/gitleaks-baseline.json --redact
```

## Warum `--no-git` statt Git-History-Scan

Ein ursprünglicher Versuch nutzte `gitleaks detect` ohne `--no-git`
(Git-History-Scan). Dabei enthält jeder Fund im Fingerprint die zugehörige
Commit-SHA. Bei `pull_request`-Triggern erzeugt GitHub bei **jedem CI-Lauf**
einen neuen, synthetischen `refs/pull/N/merge`-Commit; für Dateiinhalt, der
mehrfach in der Historie vorkommt (z. B. weil eine Zeile über mehrere Commits
hinweg wiederholt bearbeitet wurde), kann Gitleaks je nach Traversierung der
Commit-Historie eine andere "erste" Commit-SHA zuordnen als beim vorherigen
Lauf. Das machte eine commit-basierte Baseline instabil — real beobachtet:
zwei Funde (`README.md:100`, `.env.example:68`) tauchten bei jedem neuen
`pull_request`-Lauf mit einer jeweils anderen Commit-SHA im Fingerprint auf,
obwohl sich der Dateiinhalt nicht geändert hatte. Auch ein expliziter
Checkout des stabilen PR-Branch-HEAD-Commits (statt des Merge-Refs) hat dies
nicht vollständig gelöst.

**Lösung:** `--no-git` scannt ausschließlich den aktuell ausgecheckten
Dateiinhalt; der Fingerprint enthält Datei, Regel und Zeile, aber keine
Commit-SHA — dadurch unabhängig von Historie/Merge-Ref-Eigenheiten stabil.
Als Nebeneffekt verschwanden 21 der ursprünglich 24 Git-History-Funde: es
waren größtenteils Mehrfach-Vorkommen desselben Inhalts über verschiedene,
mittlerweile überschriebene historische Commits hinweg, die im **aktuellen**
Dateiinhalt gar nicht mehr in dieser Form vorkommen.

## Aktuelle Baseline (3 Funde, aktueller Dateiinhalt)

- `.env.example:293` (`OSTICKET_MINIO_SECRET`, Regel `generic-api-key`)
- `docs/16_scraping_configurator.md:157` (`NEO4J_BASIC_AUTH`, Regel `generic-api-key`)
- `docs/11_obsidian_integration.md:80` (Curl-Auth-Header, Regel `curl-auth-header`)

Nach Durchsicht handelt es sich um beispielhafte/Platzhalter-Werte im
Vorlagenformat (`.env.example`) bzw. Dokumentations-Beispiele — **dieser PR
bewertet nicht abschließend, ob einzelne Werte real und rotationspflichtig
sind** (das würde ein Lesen/Bewerten der konkreten Werte erfordern, was
außerhalb des Scopes dieses PR liegt).

## Ausdrücklicher Hinweis: Git-Historie bleibt unverändert bestehen

`--no-git` bewertet nur den aktuellen Dateiinhalt. Ältere Commits, die
frühere Versionen von `.env.example`/`README.md`/etc. mit potenziell anderen
Beispielwerten enthalten, bleiben unverändert Teil der Git-Historie dieses
Repositories — dieser PR entfernt nichts aus der Historie (kein
History-Rewrite, kein Force-Push). Das ist eine bewusste Entscheidung: Ein
History-Purge ist eine eigenständige, folgenreiche Aktion (betrifft alle
Klone/Forks) und gehört in einen separaten, dedizierten Security-PR mit
expliziter Freigabe durch den Repo-Owner, nicht in diese Governance-Baseline.

**Empfehlung (nicht Teil dieses PR):** In einem eigenen, dedizierten
Security-PR bewerten, ob die 3 aktuellen und/oder ältere historische Werte
reale, rotationspflichtige Secrets sind (dann: Rotation + ggf.
History-Purge in Abstimmung mit dem Repo-Owner), oder ob es sich um
harmlose Beispielwerte handelt (dann: Baseline-Eintrag dauerhaft
beibehalten und als "bewusst akzeptiert" kommentieren).
