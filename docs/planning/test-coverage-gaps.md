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

## `ocr-service`: Tests laufen wieder, aber nur als Unit-Test-Suite mit gemockten Engines

- **Status:** Die fruehere `fastapi`/`httpx`-Versionskollision ist durch das
  reproduzierbare Dependency-Pinning (`ocr-service/requirements.in` +
  `requirements.lock.txt`, hash-verifiziert) beseitigt. `ocr-service` hat
  wieder eine laufende, merge-kritische Testsuite: 34 Tests in
  `ocr-service/tests/test_app.py`.
- **Wie getestet wird:** Alle schweren OCR-Engines (GOT-OCR/`transformers`,
  `torch`, Tesseract) sind gemockt - die Suite prueft die FastAPI-Anwendung
  selbst (Routing, Validierung, Fehlerbehandlung), nicht die tatsaechliche
  OCR-Erkennungsqualitaet. Kein Modell-Download, kein GPU-Bedarf.
- **Sichtbarmachung in CI:** ein dedizierter `ocr-service-unit-tests`-Job in
  `.github/workflows/ci.yml` fuehrt die Suite direkt gegen das fertige
  Runtime-Image aus (analog zu `tts-service-unit-tests`) - testet damit die
  real installierten Python-/Torch-/OpenCV-Versionen. `pytest` wird dafuer
  ausschliesslich in einem ephemeren Test-Image installiert
  (`ocr-service/requirements-test.lock.txt`), das produktive
  `ci-local/ocr-service`-Image bleibt unveraendert. Der Job ist Teil von
  `ci-required`.
- **Weiterhin nicht abgedeckt:** ein echter End-to-End-Test gegen die realen
  OCR-Engines (Modell-Inferenz, Bildqualitaet, Tesseract-Erkennungsraten)
  bleibt weiterhin nicht Bestandteil dieser Unit-Test-Suite.
