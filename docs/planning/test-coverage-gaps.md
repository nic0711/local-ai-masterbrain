# Test-Coverage-Luecken (Phase 1)

> Dieses Dokument macht bekannte Test-Luecken sichtbar, statt sie stillschweigend
> zu uebergehen oder als "getestet" darzustellen.

## `tts-service`: keine automatisierten Tests

- **Fund:** Im Gegensatz zu `auth-gateway/tests/`, `ocr-service/tests/` und
  `python-nlp-service/tests/` existiert unter `tts-service/` kein `tests/`-Verzeichnis.
- **Status:** befristete Phase-2-Abweichung, nicht Gegenstand der Behebung in
  diesem PR (`agent/phase-1-governance-ci-supply-chain`).
- **Owner:** `@nic0711` (Platzhalter, zu bestaetigen).
- **Zieltermin:** spaetestens mit Abschluss von Phase 2 ("Custom Container
  haerten", siehe `docs/planning/implementation-roadmap.md`).
- **Sichtbarmachung in CI:** Der `test-presence-check`-Schritt in
  `.github/workflows/ci.yml` prueft je Custom-Service explizit auf Existenz
  eines `tests/`-Verzeichnisses und meldet das Fehlen bei `tts-service`
  sichtbar (kein Job-Fehlschlag, aber auch **kein** gruener Teststatus fuer
  einen nicht vorhandenen Test). Der `component-tests`-Job selbst fuehrt fuer
  `tts-service` bewusst **keinen** `pytest`-Lauf aus.
