# Trivy-Image-CVE-Remediation – Bestandsaufnahme und Plan

**Status: Bestandsaufnahme abgeschlossen, Plan zur Freigabe. Keine der in
Abschnitt 4 beschriebenen Remediation-PRs (A/B/C) wurde in diesem Schritt
umgesetzt. Keine Security-Exceptions, keine Scanner-/Governance-Änderung.**

## 0. Kontext

`trivy-image` (CI-Job, `--severity CRITICAL,HIGH`) konnte auf `main` ueber
laengere Zeit nicht durchlaufen, weil `build-custom-images
(python-nlp-service)` durch die spaCy/Python-3.14-Regression (Dependabot
#107) blockierte – nachgelagerte Jobs wurden uebersprungen (`skipping`).
Nach dem Fix dieser Regression (PR #122, gemergt als `9b10a97`) laeuft
`trivy-image` fuer alle vier Custom-Images zum ersten Mal seit laengerem
durch und deckt einen bisher nie ausgewerteten CVE-Bestand auf.

Verifiziert: Der PR fuer das Intune/Grafana-Feature (#121) zeigt gegenueber
`main` nach demselben Merge **keine** neuen/entfernten/verschaerften
Trivy-Findings (Vergleich pro Service: Package + InstalledVersion +
VulnerabilityID identisch, 0 Abweichungen in allen vier Services) – die hier
dokumentierten Findings sind nicht durch #121 verursacht.

Datenquelle: CI-Workflow-Run `31755814430` (PR-#121-Lauf, entspricht
`main`-Stand nach PR #122), Artefakte `trivy-report-<service>`. Rohdaten je
Service in [`trivy-inventory/<service>.csv`](trivy-inventory/),
Zusammenfassung in [`trivy-inventory/summary.json`](trivy-inventory/summary.json).

**Normalisierung:** Die gespeicherten Trivy-Inventardaten sind normalisiert.
Fluechtige CI-Merge-/Image-SHAs wurden aus den Target-Strings der
OS-Package-Findings entfernt (`ci-local/<service>:<sha> (debian X.Y)` →
`ci-local/<service> (debian X.Y)`), da sie keine fachliche Bedeutung fuer
den CVE-Vergleich haben und bei jedem CI-Lauf wechseln (Gitleaks hatte den
SHA im Trivy-Target faelschlich als `generic-api-key` erkannt). Statt des
SHA dient `source_workflow_run_id` (in `summary.json`, siehe oben) und der
jeweilige Artefaktname der Nachvollziehbarkeit. Language-Package-Targets
(z. B. `Python`, `usr/libexec/docker/cli-plugins/docker-compose`) sind
unveraendert, da sie keinen SHA enthalten.

## 1. Zahlen (verifiziert gegen die realen CI-Artefakte)

| Service | Findings gesamt | eindeutige Vuln-IDs | OS-Pkgs | Lang-Pkgs | `fixed` | `affected` | `fix_deferred` | `will_not_fix` | sonstige |
|---|---|---|---|---|---|---|---|---|---|
| auth-gateway | 43 | 28 | 37 | 6 | 4 | 25 | 13 | 1 | – |
| python-nlp-service | 39 | 24 | 37 | 2 | 2 | 23 | 13 | 1 | – |
| ocr-service | 1770 | 841 | 1768 | 2 | 1249 | 374 | 111 | 36 | – |
| tts-service | 1915 | 866 | 1913 | 2 | 1249 | 501 | 125 | 36 | 4 (`end_of_life`) |

`Status` ist Trivys eigene Klassifikation pro Finding: `fixed` = eine
`FixedVersion` ist verfuegbar (direkt behebbar durch Versions-Bump/Upgrade),
`affected`/`fix_deferred`/`will_not_fix`/`end_of_life` = kein Fix verfuegbar
oder vom Anbieter bewusst zurueckgestellt/abgelehnt.

## 2. Auth-Gateway und python-nlp-service (Debian 12.15, `python:3.14-slim-bookworm`)

- Beide Images nutzen bereits Multi-Stage-Builds mit digest-gepinntem
  `python:3.14-slim-bookworm` und fuehren bereits `apt-get upgrade -y` im
  Runtime-Stage aus (verifiziert in beiden Dockerfiles).
- Die 37 OS-Package-Findings sind zwischen beiden Services **identisch**
  (gleiches Base-Image, gleiche Debian-Version) – Fix wirkt sich auf beide
  gleich aus.
- Direkt fixbare Language-Findings (Status `fixed`, `FixedVersion`
  vorhanden):

  | Service | CVE/Advisory | Paket | Installiert | FixedVersion |
  |---|---|---|---|---|
  | beide | GHSA-6v7p-g79w-8964 | msgpack | 1.1.2 | 1.2.1 |
  | beide | CVE-2025-47273 | setuptools | 70.3.0 | 78.1.1 |
  | nur auth-gateway | CVE-2026-34040 | github.com/docker/docker (Docker-CLI-Plugin) | v28.5.2+incompatible | 29.3.1 |
  | nur auth-gateway | CVE-2026-39822 | stdlib (Go, im selben Binary) | v1.26.4 | 1.25.12 / 1.26.5 / 1.27.0-rc.2 |

- Die verbleibenden 37 OS-Package-Findings pro Service haben **keine**
  `FixedVersion` (`affected`/`fix_deferred`/`will_not_fix`) – das sind
  Debian-Bookworm-Pakete, fuer die der Debian Security Tracker selbst noch
  keinen Fix bereitstellt. Ueber `apt-get upgrade` (bereits vorhanden) nicht
  weiter reduzierbar, solange Debian keinen Patch veroeffentlicht.

## 3. OCR-Service und TTS-Service (Debian 11.11, `python:3.13-bullseye`)

- Beide Images: **Single-Stage-Build**, Base-Image **ohne Digest-Pin**
  (`FROM python:3.13-bullseye`), kein `apt-get upgrade` im Dockerfile.
  Build-/Dev-Pakete (Compiler, Header) verbleiben im Runtime-Image, da kein
  Builder-Stage existiert, der sie abtrennen koennte.
- Debian 11 (bullseye) ist deutlich aelter als Debian 12 (bookworm, bei
  Auth/NLP) – das erklaert die Groessenordnung: 841 bzw. 866 eindeutige
  Vulnerability-IDs gegenueber 28/24 bei Auth/NLP.
- **1249 der `fixed`-Findings sind zwischen OCR und TTS exakt identisch**
  (gleiches Package + gleiche InstalledVersion + gleiche VulnerabilityID) –
  ein Base-Image-Wechsel wirkt sich auf beide nahezu gleich aus, auch wenn
  sie aus Risikogruenden (ML/Audio-Abhaengigkeiten) in getrennten PRs
  bearbeitet werden (siehe Abschnitt 4).
- 1249 von ~1770/1915 Findings haben bereits eine `FixedVersion` verfuegbar
  – das ist der groesste Hebel: ein Wechsel auf eine aktuell unterstuetzte
  Debian-Basis (bzw. mindestens ein volles `apt-get upgrade` auf der
  aktuellen Basis, falls ein Versionswechsel nicht sofort moeglich ist)
  wuerde den Grossteil dieser Findings ohne Anwendungscode-Aenderung
  beheben.

## 4. Remediation-Plan – aufgeteilt in drei unabhaengige PRs

**Keiner dieser PRs wurde in diesem Schritt umgesetzt.** Reihenfolge nach
Groesse des Hebels, nicht nach Abhaengigkeit – die drei PRs sind
voneinander unabhaengig.

### PR A – OCR-Image-Hardening

Ziel: OCR-Service auf eine aktuell unterstuetzte, bevorzugt `slim`-Debian-
Basis migrieren, Digest pinnen, auf Multi-Stage umstellen (Compiler/
Header/`-dev`-Pakete nur im Builder-Stage), `apt-get upgrade` im
Runtime-Stage ergaenzen.

Vorgehen (nicht blind auf ein Zielimage festlegen):
1. Kompatibilitaets-Build gegen Kandidaten-Basis(en) real durchfuehren
   (TrOCR/Tesseract-Abhaengigkeiten pruefen, insbesondere native
   Bibliotheken).
2. Multi-Stage-Dockerfile erstellen, Runtime-Stage minimal halten.
3. OCR-Funktion vollstaendig testen (Component-Tests + Endpoints).
4. Trivy vorher/nachher vergleichen, Ergebnis im PR dokumentieren.

### PR B – TTS-Image-Hardening

Gleiches Verfahren wie PR A, **separat**, nicht mit OCR im selben PR – TTS
hat eigene ML/Audio-Abhaengigkeiten mit eigenstaendigem Kompatibilitaets-
/Regressionsrisiko, das nicht mit dem OCR-Risiko vermischt werden soll.

### PR C – Auth-Gateway/python-nlp-service: verbleibende fixbare Findings

Nur die in Abschnitt 2 gelisteten Findings mit `FixedVersion` anfassen:
- `msgpack` 1.1.2 → 1.2.1 (auth-gateway + python-nlp-service)
- `setuptools` 70.3.0 → 78.1.1 (auth-gateway + python-nlp-service)
- Docker-CLI-Plugin (`github.com/docker/docker`) → 29.3.1 (nur auth-gateway)
- Go-`stdlib` im selben Binary → 1.25.12/1.26.5/1.27.0-rc.2 (nur
  auth-gateway)

Nur upgraden, wenn Build + Tests + Smoke-Test grün bleiben. Kein Wechsel
der Debian-Basis noetig (37 verbleibende OS-Findings haben keine
`FixedVersion`, siehe Abschnitt 2 – dafuer ist kein Fix verfuegbar, nicht
Teil dieses PR).

## 5. Security-Exceptions – erst nach Abschluss von PR A–C

Nur Findings **ohne verfuegbaren Fix** (`affected`/`fix_deferred`/
`will_not_fix`, kein `FixedVersion`) duerfen ueberhaupt fuer eine Ausnahme
geprueft werden. Kein Finding mit vorhandener `FixedVersion` bekommt eine
Ausnahme, ausser bei nachgewiesenem, konkretem Kompatibilitaetsblocker.

Jede einzelne Ausnahme (kein Pauschal-/Massen-Ignore) strukturiert mit:
CVE/Advisory, Package, InstalledVersion, Image/Digest, Begruendung, reale
Exposure, Owner, Ablaufdatum, Approval – analog zum bestehenden
`docs/planning/gitleaks-baseline.md`-Muster fuer den Secret-Scanner.

## 6. CI-Governance – Vorschlag fuer danach

Nicht Teil dieses Schritts. Aktuelles Problem: Das Modell macht jeden
fachlich unabhaengigen PR rot, solange bestehende Image-Schulden
existieren (siehe #121, das trotz nachgewiesener Nicht-Regression rot
bleibt). Nach Abschluss von PR A–C wird ein separates Governance-Design
vorgeschlagen:
- vollstaendige Trivy-Reports bleiben immer sichtbar (Artefakt, wie bisher)
- bestehende, bestaetigte Security-Debt wird separat getrackt statt den
  PR-Gate zu blockieren
- PR-Gate blockiert gezielt NEUE bzw. verschlechterte Critical/High-
  Findings gegenueber `main` (Diff-Ansatz, wie in Abschnitt 0 manuell fuer
  #121 durchgefuehrt)
- bereits behobene Findings duerfen nicht wieder eingefuehrt werden
- echte Ausnahmen bleiben weiterhin einzeln strukturiert und befristet
  (Abschnitt 5)

Diese Aenderung wird erst nach PR A–C und mit belastbaren
Vorher/Nachher-Zahlen vorgeschlagen, nicht jetzt nebenbei implementiert.
