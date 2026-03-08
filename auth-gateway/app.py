import os
import logging
from flask import Flask, request, jsonify
from supabase import create_client, Client

# Logging konfigurieren
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

# Supabase-Client aus Umgebungsvariablen initialisieren
try:
    url: str = os.environ.get("SUPABASE_URL")
    key: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
    supabase: Client = create_client(url, key)
    logging.info("Supabase client initialized successfully.")
except Exception as e:
    logging.error(f"Failed to initialize Supabase client: {e}")
    supabase = None

@app.route('/health', methods=['GET'])
def health():
    """Health Check Endpoint für Docker und Caddy."""
    if supabase is None:
        return "Service Unavailable", 503
    return "OK", 200

@app.route('/verify', methods=['GET'])
def verify_auth():
    if not supabase:
        return "Auth service not configured", 500

    # Primär: Caddy übergibt den Auth-Token im 'Authorization'-Header
    # (gesetzt via header_up aus dem sb-access-token Cookie)
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        jwt = auth_header.split(' ', 1)[1]
    else:
        # Fallback: Token direkt aus Cookie lesen
        jwt = request.cookies.get('sb-access-token')
        if not jwt:
            logging.warning("No valid Authorization header or sb-access-token cookie found.")
            return "Unauthorized", 401

    try:
        # Überprüfe die Gültigkeit des JWT mit Supabase
        user_response = supabase.auth.get_user(jwt)
        if user_response.user:
            logging.info(f"Successfully authenticated user: {user_response.user.id}")
            return "OK", 200
    except Exception as e:
        logging.error(f"JWT validation error: {e}")
        # Absichtlich keine Details leaken, einfach ablehnen

    # Kein Token-Fragment loggen – verhindert versehentliche Credential-Exposition
    logging.warning("Failed authentication attempt - invalid or expired token.")
    return "Unauthorized", 401