# Security-Ausnahmen

Dieses Verzeichnis liegt unter dem Schutz von `.github/CODEOWNERS`
(`/docs/planning/`). Jede aktive Ausnahme wird als eigene `.yml`-Datei nach
dem Schema in `.github/security-exceptions.template.yml` abgelegt.

Aktuell sind **keine** Ausnahmen aktiv — dieses Verzeichnis ist zum Zeitpunkt
von PR `agent/phase-1-governance-ci-supply-chain` leer (nur diese README hält
das Verzeichnis versioniert). `scripts/ci/validate-exceptions.py` behandelt
ein leeres Verzeichnis als "nichts zu prüfen", nicht als Fehler.

Eine Ausnahme gilt erst dann als freigegeben, wenn ihre Datei über einen
echten GitHub-PR-Review gemäß der Freigabe-Matrix in
`docs/handbook/09-verantwortlichkeiten.md` gemerged wurde — niemals allein
durch einen Eintrag in ihrer eigenen `approvals`-Liste.
