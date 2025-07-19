from flask import Flask, jsonify, request
import logging
import sys
import traceback
import spacy

app = Flask(__name__)

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Globale Variablen
service_ready = False
nlp = None

def initialize_nlp_models():
    """Initialisiere NLP-Modelle hier"""
    global service_ready, nlp
    try:
        # Deutsches spaCy-Modell laden
        logger.info("Lade deutsches spaCy-Modell 'de_core_news_sm'...")
        nlp = spacy.load("de_core_news_sm")
        
        logger.info("NLP-Modelle erfolgreich geladen")
        service_ready = True
        return True
    except Exception as e:
        logger.error(f"Fehler beim Laden der NLP-Modelle: {e}")
        logger.error(traceback.format_exc())
        service_ready = False
        return False

@app.route('/health', methods=['GET'])
def health_check():
    """Health Check Endpoint für Docker"""
    try:
        if service_ready:
            return jsonify({
                "status": "healthy",
                "service": "python-nlp-service",
                "ready": True
            }), 200
        else:
            return jsonify({
                "status": "starting",
                "service": "python-nlp-service", 
                "ready": False
            }), 503
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "error",
            "service": "python-nlp-service",
            "error": str(e)
        }), 500

@app.route('/status', methods=['GET'])
def status():
    """Detaillierter Status-Endpoint"""
    return jsonify({
        "service": "python-nlp-service",
        "ready": service_ready,
        "version": "1.0.0",
        "endpoints": ["/health", "/status", "/process"]
    })

@app.route('/process', methods=['POST'])
def process_text():
    """Hauptverarbeitungsendpoint"""
    if not service_ready or not nlp:
        return jsonify({
            "error": "Service not ready"
        }), 503
    
    try:
        data = request.get_json()
        text = data.get('text')
        if not text:
            return jsonify({"error": "Kein 'text' im Request gefunden."}), 400
        
        # NLP-Verarbeitung mit spaCy: Entitätserkennung
        doc = nlp(text)
        entities = [{"text": ent.text, "label": ent.label_} for ent in doc.ents]
        
        result = {
            "original_text": text,
            "processed": True,
            "length": len(text),
            "entities": entities
        }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Verarbeitungsfehler: {e}")
        return jsonify({
            "error": str(e)
        }), 500

# Initialisiere die Modelle beim Start der Anwendung
logger.info("Starte Python NLP Service...")
initialize_nlp_models()

if __name__ == '__main__':
    # Dieser Block wird nur für lokales Debugging ohne Docker/Gunicorn verwendet
    logger.info("Starte Flask Development Server für lokales Debugging...")
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )