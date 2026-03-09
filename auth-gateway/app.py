import os
import time
import logging
import urllib.request
import urllib.error
from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from supabase import create_client, Client

# Logging konfigurieren
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://",
)

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

# Backup file paths
_BACKUP_TRIGGER = os.environ.get("BACKUP_TRIGGER_FILE", "/opt/backups/.trigger")
_BACKUP_STATUS  = os.environ.get("BACKUP_STATUS_FILE",  "/opt/backups/.backup_status")


@app.route('/health', methods=['GET'])
def health():
    """Health Check Endpoint für Docker und Caddy."""
    if supabase is None:
        return "Service Unavailable", 503
    return "OK", 200

# Service health check map: name → (host, port, path)
_SERVICES = {
    "n8n":                ("n8n", 5678, "/healthz"),
    "open-webui":         ("open-webui", 8080, "/health"),
    "flowise":            ("flowise", 3001, "/api/v1/ping"),
    "langfuse":           ("langfuse-web", 3000, "/api/public/health"),
    "neo4j":              ("neo4j", 7474, "/"),
    "qdrant":             ("qdrant", 6333, "/healthz"),
    "crawl4ai":           ("crawl4ai", 11235, "/health"),
    "searxng":            ("searxng", 8080, "/healthz"),
    "python-nlp-service": ("python-nlp-service", 5000, "/health"),
    "supabase":           ("supabase-auth", 9999, "/health"),
    "minio":              ("localai-minio-1", 9000, "/minio/health/live"),
    "clickhouse":         ("clickhouse", 8123, "/ping"),
    "obsidian":           ("host.docker.internal", 27123, "/"),
}

def _ping(host: str, port: int, path: str) -> bool:
    try:
        url = f"http://{host}:{port}{path}"
        req = urllib.request.urlopen(url, timeout=3)
        return req.status < 500
    except Exception:
        return False


@app.route('/status', methods=['GET'])
def service_status():
    """Aggregierter Health-Status aller Services – für das Dashboard."""
    result = {}
    for name, (host, port, path) in _SERVICES.items():
        result[name] = "up" if _ping(host, port, path) else "down"
    return jsonify(result), 200


def _get_verified_user():
    """Extracts JWT from Authorization header or sb-access-token cookie and validates it.
    Returns the user object on success, or None on failure."""
    if not supabase:
        return None

    # Primär: Authorization-Header (gesetzt von Caddy via header_up)
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        jwt = auth_header.split(' ', 1)[1]
    else:
        # Fallback: Token direkt aus Cookie lesen
        jwt = request.cookies.get('sb-access-token')
        if not jwt:
            return None

    try:
        user_response = supabase.auth.get_user(jwt)
        if user_response.user:
            return user_response.user
    except Exception as e:
        logging.error(f"JWT validation error: {e}")

    return None


@app.route('/verify', methods=['GET'])
@limiter.limit("20 per minute")
def verify_auth():
    if not supabase:
        return "Auth service not configured", 500

    user = _get_verified_user()
    if user:
        logging.info(f"Successfully authenticated user: {user.id}")
        return "OK", 200

    # Kein Token-Fragment loggen – verhindert versehentliche Credential-Exposition
    logging.warning("Failed authentication attempt - invalid or expired token.")
    return "Unauthorized", 401


@app.route('/control/backup', methods=['POST'])
def trigger_backup():
    """Schreibt eine Trigger-Datei, die vom backup-daemon aufgegriffen wird."""
    user = _get_verified_user()
    if not user:
        logging.warning("Unauthorized backup trigger attempt.")
        return jsonify({"error": "Unauthorized"}), 401

    try:
        trigger_dir = os.path.dirname(_BACKUP_TRIGGER)
        os.makedirs(trigger_dir, exist_ok=True)
        with open(_BACKUP_TRIGGER, 'w') as f:
            f.write(str(int(time.time())))
        logging.info(f"Backup triggered by user: {user.id}")
        return jsonify({"status": "triggered"}), 200
    except Exception as e:
        logging.error(f"Failed to write backup trigger file: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route('/control/backup/status', methods=['GET'])
def backup_status():
    """Liest den Backup-Status aus der Status-Datei. Keine Auth erforderlich."""
    try:
        with open(_BACKUP_STATUS, 'r') as f:
            content = f.read().strip()
        parts = content.split(':', 1)
        status_key = parts[0] if len(parts) > 0 else 'unknown'
        timestamp_val = int(parts[1]) if len(parts) > 1 else None
        return jsonify({"status": status_key, "timestamp": timestamp_val}), 200
    except Exception:
        return jsonify({"status": "unknown", "timestamp": None}), 200
