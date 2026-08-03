# Gitleaks-Baseline (Bestandsfindings)

`docs/planning/gitleaks-baseline.json` ist eine maschinell erzeugte Baseline
(`gitleaks detect --report-format json`) der zum Zeitpunkt von
`agent/phase-1-governance-ci-supply-chain` bereits in der Git-Historie
vorhandenen Findings. Sie wurde erzeugt mit:

```bash
docker run --rm -v "$PWD":/repo \
  zricethezav/gitleaks@sha256:c00b6bd0aeb3071cbcb79009cb16a60dd9e0a7c60e2be9ab65d25e6bc8abbb7f \
  detect --source=/repo --report-format json --report-path /repo/docs/planning/gitleaks-baseline.json --redact
```

**Fund:** 24 Treffer, ausschließlich in bereits lange bestehenden Commits
(überwiegend vom ursprünglichen Upstream-Autor), in `.env.example` (Platzhalter-
/Beispielwerte im Vorlagenformat), sowie in Doku-Beispielen (`docs/02_configuration.md`,
`docs/11_obsidian_integration.md`, `docs/16_scraping_configurator.md`,
`README.md`, `.agents/plans/completed/02-auth-database.md`). Es handelt sich
nach Durchsicht um beispielhafte/Platzhalter-Werte im JWT-/API-Key-Format, wie
sie in Setup-Dokumentation und `.env.example`-Vorlagen typisch sind — **dieser
PR bewertet nicht abschließend, ob einzelne Werte real und rotationspflichtig
sind** (das würde ein Lesen/Bewerten der konkreten Werte erfordern, was
außerhalb des Scopes dieses PR liegt und gemäß Arbeitsauftrag unterbleibt).

**Warum eine Baseline statt Bereinigung:** Diese Funde liegen in bereits
gemergter Git-Historie. Sie in diesem PR zu entfernen würde entweder History-
Rewriting (Force-Push, explizit verboten) oder das Ändern von `.env.example`
(außerhalb des Scope dieses PR) erfordern. Die Baseline unterdrückt diese
Funde **nicht dauerhaft und nicht pauschal für alle Findings** — sie wirkt
ausschließlich auf exakt diese 24, bereits bekannten Treffer. Jeder **neue**
Fund (z. B. ein in diesem oder einem künftigen PR neu committeter Secret-Wert)
wird vom `secret-scan`-Job weiterhin sofort und blockierend gemeldet.

**Empfehlung (nicht Teil dieses PR):** In einem eigenen, dedizierten
Security-PR bewerten, ob einzelne der 24 Werte reale, rotationspflichtige
Secrets sind (dann: Rotation + ggf. History-Purge in Abstimmung mit dem
Repo-Owner), oder ob es sich um harmlose Beispielwerte handelt (dann:
Baseline-Eintrag dauerhaft beibehalten und ggf. als "bewusst akzeptiert"
kommentieren).
