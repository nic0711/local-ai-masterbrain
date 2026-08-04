# ADR 0009: Document API und separate OCR Engine

- Status: Akzeptiert
- Datum: 2026-08-03

## Kontext

Der bestehende NLP-/Dokumentendienst und der OCR-Service enthalten überlappende
PDF-, OCR- und Konvertierungslogik.

## Entscheidung

Die `document-api` übernimmt Dokumentannahme, PDF-Verarbeitung, Extraktion,
NER, Engine-Auswahl und Ergebnisnormalisierung.

Die `ocr-engine` übernimmt ausschließlich OCR-Ausführung.

Die Migration erfolgt schrittweise über eine Kompatibilitätsschicht. Alte
Endpunkte werden frühestens nach zwei geprüften Stack-Releases und ohne
produktive Nutzung entfernt.

## Folgen

Eine fachliche Dokumenten-API, austauschbare OCR-Engines und keine dauerhaft
doppelte Geschäftslogik.
