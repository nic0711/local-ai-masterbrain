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

## `ocr-service`: vorhandene Tests koennen aktuell nicht ausgefuehrt werden

- **Fund (waehrend Phase-1-Validierung tatsaechlich reproduziert, sowohl lokal
  in einem frischen venv als auch im per `docker build` erzeugten Custom
  Image `ci-local/ocr-service:test`):** `ocr-service/requirements.txt` pinnt
  `fastapi==0.104.1` (zieht `starlette==0.27.0`), laesst `httpx` aber
  ungepinnt. Ein frischer `pip install` installiert `httpx==0.28.1`, dessen
  `Client.__init__` das von `starlette==0.27.0`s `TestClient` verwendete
  Schluesselwortargument `app=` nicht mehr akzeptiert. Ergebnis:
  ```
  tests/test_app.py:101: in <module>
      client = TestClient(app_module.app)
  TypeError: Client.__init__() got an unexpected keyword argument 'app'
  ```
  Exit-Code: `2` (Pytest-Collection-Fehler, kein einziger Test lief).
- **Status:** befristete Phase-2-Abweichung (Dependency-Pinning-Haertung),
  nicht Gegenstand der Behebung in diesem PR — `ocr-service/requirements.txt`
  gehoert laut Plan nicht zu den in Phase 1 zu aendernden Dateien.
- **Owner:** `@nic0711` (Platzhalter, zu bestaetigen).
- **Zieltermin:** spaetestens mit Abschluss von Phase 2.
- **Sichtbarmachung in CI:** `ocr-service` ist bewusst nicht Teil der
  `component-tests`-Matrix in `.github/workflows/ci.yml` (mit Kommentar, der
  auf diesen Abschnitt verweist), damit der Pflicht-Check nicht dauerhaft an
  einem bereits bekannten, unabhaengig von diesem PR bestehenden Fund
  scheitert. `test-presence-check` bestaetigt weiterhin, dass ein
  `tests/`-Verzeichnis fuer `ocr-service` existiert — nur die Ausfuehrbarkeit
  ist betroffen.
