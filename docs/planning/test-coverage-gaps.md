# Test-Coverage-Luecken (Phase 1)

> Dieses Dokument macht bekannte Test-Luecken sichtbar, statt sie stillschweigend
> zu uebergehen oder als "getestet" darzustellen.

## `tts-service`: Regressionstests fuer die Audio-Ausgabekonvertierung, keine vollstaendige TTS-/Dubbing-Abdeckung

- **Fund (urspruenglich):** Im Gegensatz zu `auth-gateway/tests/`,
  `ocr-service/tests/` und `python-nlp-service/tests/` existierte unter
  `tts-service/` kein `tests/`-Verzeichnis.
- **Status (aktuell, seit `tts-service/tests/test_tts_engine.py`, siehe
  Issue #142):** `tts-service` hat jetzt gezielte Regressionstests fuer den
  Audio-Ausgabekonvertierungspfad in `tts_engine.py`
  (`_synthesize_sync`/`_audio_to_numpy`) - u. a. den konkreten Bug, der zu
  `AttributeError: 'numpy.ndarray' object has no attribute 'cpu'` bei jedem
  `/tts/synthesize`- und `/tts/clone`-Aufruf fuehrte. Die Tests laufen ohne
  echten OmniVoice-Modell-Download gegen ein Fake-Modell und pruefen sowohl
  `numpy.ndarray`- als auch `torch.Tensor`-Rueckgaben sowie das Verhalten bei
  unerwarteten Typen.
- **Weiterhin nicht abgedeckt (keine Uebertreibung der Testabdeckung):** Die
  uebrigen Endpunkte (`/voices`, `/dub/video`, `/dub/status`,
  `/dub/download`), die Dubbing-Pipeline (`dubbing.py`, faster-whisper,
  Ollama-Integration) und ein echter End-to-End-Lauf gegen die reale
  OmniVoice-Engine sind **nicht** Teil der automatisierten CI-Testsuite -
  dafuer bleibt weiterhin nur der manuelle Test gegen das reale Image (siehe
  PR-Beschreibung zu Issue #142).
- **Owner:** `@nic0711` (Platzhalter, zu bestaetigen).
- **Zieltermin fuer vollstaendige Abdeckung:** offen, kein neuer PR-Scope.
- **Sichtbarmachung in CI:** `test-presence-check` prueft ab sofort ohne
  Sonderfall fuer `tts-service` (das `tests/`-Verzeichnis existiert). Ein
  dedizierter `tts-service-unit-tests`-Job in `.github/workflows/ci.yml`
  fuehrt die Tests direkt im fertigen Runtime-Image aus (per
  `unittest discover`, kein `pytest` im Image noetig, kein Modell-Download,
  keine Secrets) - testet damit exakt die Python-/Torch-/Soundfile-Versionen,
  die spaeter produktiv laufen.

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
