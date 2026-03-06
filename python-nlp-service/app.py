import os
import base64
import logging
import sys
import traceback

import fitz  # PyMuPDF
import requests
import spacy
from flask import Flask, jsonify, request

app = Flask(__name__)

# Schutz vor übermäßig großen Eingaben (DoS-Prävention)
MAX_TEXT_LENGTH = 50_000  # ~50k Zeichen ≈ 10k Tokens
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

# Konfiguration aus Umgebungsvariablen
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://host.docker.internal:11434")
OCR_MODEL = os.environ.get("OCR_MODEL", "glm-ocr")

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Globale Variablen
service_ready = False
nlp_models = {}  # {"de": model, "en": model}

SUPPORTED_LANGUAGES = ("de", "en")
SPACY_MODELS = {
    "de": "de_core_news_md",
    "en": "en_core_web_md",
}


def initialize_nlp_models():
    global service_ready, nlp_models
    try:
        for lang, model_name in SPACY_MODELS.items():
            logger.info(f"Lade spaCy-Modell '{model_name}'...")
            nlp_models[lang] = spacy.load(model_name)
        logger.info("Alle NLP-Modelle erfolgreich geladen")
        service_ready = True
        return True
    except Exception as e:
        logger.error(f"Fehler beim Laden der NLP-Modelle: {e}")
        logger.error(traceback.format_exc())
        service_ready = False
        return False


def _get_nlp(lang: str):
    return nlp_models.get(lang) or nlp_models.get("de")


def _extract_entities(text: str, lang: str) -> list:
    nlp = _get_nlp(lang)
    doc = nlp(text)
    return [
        {
            "text": ent.text,
            "label": ent.label_,
            "start": ent.start_char,
            "end": ent.end_char,
        }
        for ent in doc.ents
    ]


def _pdf_extract_text(pdf_bytes: bytes) -> tuple[str, int]:
    """Direkte Textextraktion aus PDF. Gibt (text, page_count) zurück."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page_count = len(doc)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text, page_count


def _pdf_to_png_pages(pdf_bytes: bytes, dpi_scale: float = 2.0) -> list[bytes]:
    """Konvertiert alle PDF-Seiten zu PNG-Bytes (für OCR)."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    mat = fitz.Matrix(dpi_scale, dpi_scale)
    pages = []
    for page in doc:
        pix = page.get_pixmap(matrix=mat)
        pages.append(pix.tobytes("png"))
    doc.close()
    return pages


def _needs_ocr(text: str) -> bool:
    """Heuristik: Weniger als 50 Zeichen → wahrscheinlich gescanntes PDF."""
    return len(text.strip()) < 50


def _ocr_image_with_ollama(image_bytes: bytes) -> str:
    """Sendet ein Bild an Ollama (glm-ocr) und gibt den extrahierten Text zurück."""
    img_b64 = base64.b64encode(image_bytes).decode()
    try:
        resp = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": OCR_MODEL,
                "prompt": (
                    "Extract all text from this image exactly as it appears. "
                    "Return only the extracted text, no explanations or comments."
                ),
                "images": [img_b64],
                "stream": False,
            },
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json().get("response", "")
    except requests.exceptions.ConnectionError:
        raise RuntimeError(f"Ollama nicht erreichbar unter {OLLAMA_HOST}")
    except requests.exceptions.Timeout:
        raise RuntimeError("Ollama OCR Timeout (>120s)")
    except Exception as e:
        raise RuntimeError(f"Ollama OCR Fehler: {e}")


# ---------------------------------------------------------------------------
# Health & Status
# ---------------------------------------------------------------------------

@app.route('/health', methods=['GET'])
def health_check():
    if service_ready:
        return jsonify({"status": "healthy", "service": "python-nlp-service", "ready": True}), 200
    return jsonify({"status": "starting", "service": "python-nlp-service", "ready": False}), 503


@app.route('/status', methods=['GET'])
def status():
    return jsonify({
        "service": "python-nlp-service",
        "ready": service_ready,
        "version": "2.0.0",
        "models": {lang: name for lang, name in SPACY_MODELS.items()},
        "ocr_model": OCR_MODEL,
        "ollama_host": OLLAMA_HOST,
        "endpoints": [
            "/health", "/status",
            "/process",
            "/pdf/analyze-type", "/pdf/to-png-smart", "/pdf/extract",
            "/document/analyze",
        ],
    })


# ---------------------------------------------------------------------------
# NLP: Named Entity Recognition
# ---------------------------------------------------------------------------

@app.route('/process', methods=['POST'])
def process_text():
    """Text → NER Entities. Body: {text, lang?}"""
    if not service_ready:
        return jsonify({"error": "Service not ready"}), 503

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "JSON body erwartet"}), 400

    text = data.get('text', '')
    lang = data.get('lang', 'de')
    if lang not in SUPPORTED_LANGUAGES:
        lang = 'de'

    if not text:
        return jsonify({"error": "Kein 'text' im Request gefunden"}), 400
    if len(text) > MAX_TEXT_LENGTH:
        return jsonify({"error": f"Text zu lang. Maximum: {MAX_TEXT_LENGTH} Zeichen"}), 413

    try:
        entities = _extract_entities(text, lang)
        return jsonify({
            "original_text": text,
            "processed": True,
            "length": len(text),
            "language": lang,
            "entities": entities,
        })
    except Exception:
        logger.error(traceback.format_exc())
        return jsonify({"error": "Verarbeitungsfehler"}), 500


# ---------------------------------------------------------------------------
# PDF: Kompatibilitäts-Endpoints (bestehender n8n Workflow)
# ---------------------------------------------------------------------------

@app.route('/pdf/analyze-type', methods=['POST'])
def analyze_pdf_type():
    """PDF → {extracted_text, needs_ocr, page_count}. Multipart: file=<pdf>"""
    if 'file' not in request.files:
        return jsonify({"error": "Kein 'file' im Request"}), 400

    pdf_bytes = request.files['file'].read()
    if len(pdf_bytes) > MAX_FILE_SIZE:
        return jsonify({"error": "Datei zu groß (max 50 MB)"}), 413

    try:
        text, page_count = _pdf_extract_text(pdf_bytes)
        return jsonify({
            "extracted_text": text,
            "needs_ocr": _needs_ocr(text),
            "page_count": page_count,
        })
    except Exception:
        logger.error(traceback.format_exc())
        return jsonify({"error": "PDF-Analyse fehlgeschlagen"}), 500


@app.route('/pdf/to-png-smart', methods=['POST'])
def pdf_to_png_smart():
    """PDF → PNG-Seiten als base64. Multipart: file=<pdf>"""
    if 'file' not in request.files:
        return jsonify({"error": "Kein 'file' im Request"}), 400

    pdf_bytes = request.files['file'].read()
    if len(pdf_bytes) > MAX_FILE_SIZE:
        return jsonify({"error": "Datei zu groß (max 50 MB)"}), 413

    try:
        png_pages = _pdf_to_png_pages(pdf_bytes)
        return jsonify({
            "pages": [
                {"page": i + 1, "image_base64": base64.b64encode(p).decode()}
                for i, p in enumerate(png_pages)
            ],
            "page_count": len(png_pages),
        })
    except Exception:
        logger.error(traceback.format_exc())
        return jsonify({"error": "PDF→PNG Konvertierung fehlgeschlagen"}), 500


@app.route('/pdf/extract', methods=['POST'])
def pdf_extract():
    """PDF → Text (direkt oder via glm-ocr). Multipart: file=<pdf>"""
    if 'file' not in request.files:
        return jsonify({"error": "Kein 'file' im Request"}), 400

    pdf_bytes = request.files['file'].read()
    if len(pdf_bytes) > MAX_FILE_SIZE:
        return jsonify({"error": "Datei zu groß (max 50 MB)"}), 413

    try:
        text, page_count = _pdf_extract_text(pdf_bytes)
        needs_ocr = _needs_ocr(text)

        if needs_ocr:
            logger.info("Gescanntes PDF erkannt – starte OCR via Ollama")
            png_pages = _pdf_to_png_pages(pdf_bytes)
            text = "\n\n".join(_ocr_image_with_ollama(p) for p in png_pages)

        return jsonify({
            "text": text,
            "needs_ocr": needs_ocr,
            "page_count": page_count,
        })
    except RuntimeError as e:
        logger.error(str(e))
        return jsonify({"error": str(e)}), 502
    except Exception:
        logger.error(traceback.format_exc())
        return jsonify({"error": "PDF-Extraktion fehlgeschlagen"}), 500


# ---------------------------------------------------------------------------
# Haupt-Endpoint: Dokument analysieren (Text + Entities)
# ---------------------------------------------------------------------------

@app.route('/document/analyze', methods=['POST'])
def document_analyze():
    """
    Universeller Dokument-Analyse-Endpoint.
    Input:  multipart (file=<pdf|bild>) ODER JSON {text, lang?}
    Output: {text, entities, needs_ocr, language, entity_count}
    """
    if not service_ready:
        return jsonify({"error": "Service not ready"}), 503

    lang = request.form.get('lang', 'de') or 'de'
    if lang not in SUPPORTED_LANGUAGES:
        lang = 'de'

    text = ""
    needs_ocr = False

    try:
        if 'file' in request.files:
            file = request.files['file']
            filename = (file.filename or "").lower()
            file_bytes = file.read()

            if len(file_bytes) > MAX_FILE_SIZE:
                return jsonify({"error": "Datei zu groß (max 50 MB)"}), 413

            if filename.endswith('.pdf'):
                text, _ = _pdf_extract_text(file_bytes)
                if _needs_ocr(text):
                    needs_ocr = True
                    logger.info("Gescanntes PDF erkannt – starte OCR via Ollama")
                    png_pages = _pdf_to_png_pages(file_bytes)
                    text = "\n\n".join(_ocr_image_with_ollama(p) for p in png_pages)
            else:
                # Bild-Datei direkt an OCR
                needs_ocr = True
                text = _ocr_image_with_ollama(file_bytes)

        else:
            data = request.get_json(silent=True) or {}
            text = data.get('text', '')
            lang = data.get('lang', lang)
            if lang not in SUPPORTED_LANGUAGES:
                lang = 'de'

        if not text:
            return jsonify({"error": "Kein Text konnte extrahiert werden"}), 400
        if len(text) > MAX_TEXT_LENGTH:
            return jsonify({"error": f"Text zu lang. Maximum: {MAX_TEXT_LENGTH} Zeichen"}), 413

        entities = _extract_entities(text, lang)

        return jsonify({
            "text": text,
            "entities": entities,
            "entity_count": len(entities),
            "needs_ocr": needs_ocr,
            "language": lang,
        })

    except RuntimeError as e:
        logger.error(str(e))
        return jsonify({"error": str(e)}), 502
    except Exception:
        logger.error(traceback.format_exc())
        return jsonify({"error": "Analyse fehlgeschlagen"}), 500


# ---------------------------------------------------------------------------
# Start
# ---------------------------------------------------------------------------

logger.info("Starte Python NLP/Document Service...")
initialize_nlp_models()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
