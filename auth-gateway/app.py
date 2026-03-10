import os
import re
import time
import glob
import json
import tarfile
import difflib
import logging
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from types import SimpleNamespace
import jwt as pyjwt
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
    except urllib.error.HTTPError as e:
        # 4xx = Service läuft, braucht nur Auth → "up"
        return e.code < 500
    except Exception:
        return False


@app.route('/status', methods=['GET'])
def service_status():
    """Aggregierter Health-Status aller Services – parallel gepingt."""
    def check(name, host, port, path):
        return name, "up" if _ping(host, port, path) else "down"

    result = {}
    with ThreadPoolExecutor(max_workers=len(_SERVICES)) as ex:
        futures = {ex.submit(check, n, h, p, path): n for n, (h, p, path) in _SERVICES.items()}
        for future in as_completed(futures):
            name, status = future.result()
            result[name] = status
    return jsonify(result), 200


# Lokale JWT-Verifikation: kein HTTP-Call zu Supabase nötig
_JWT_SECRET = os.environ.get("JWT_SECRET", "")

# Cache für lokale Verifikationsergebnisse (Speicherschutz, max. 500 Einträge)
_jwt_cache: dict = {}
_JWT_CACHE_TTL = 300  # 5 Minuten – großzügig, da lokal verifiziert
_JWT_CACHE_MAX = 500


def _get_verified_user():
    """Validiert JWT lokal via PyJWT (kein Supabase-HTTP-Call).
    Fallback auf Supabase-API wenn JWT_SECRET nicht gesetzt."""
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header.split(' ', 1)[1]
    else:
        token = request.cookies.get('sb-access-token')
        if not token:
            return None

    now = time.time()
    cache_key = token[-32:]

    # Cache-Lookup
    cached = _jwt_cache.get(cache_key)
    if cached:
        user, expires_at = cached
        if now < expires_at:
            return user
        del _jwt_cache[cache_key]

    user = None

    if _JWT_SECRET:
        # Schneller Pfad: lokale kryptografische Verifikation (<1ms)
        try:
            payload = pyjwt.decode(
                token, _JWT_SECRET, algorithms=["HS256"],
                options={"verify_aud": False},
            )
            user = SimpleNamespace(
                id=payload.get("sub", ""),
                email=payload.get("email", ""),
            )
        except pyjwt.ExpiredSignatureError:
            return None
        except pyjwt.InvalidTokenError:
            return None
    elif supabase:
        # Fallback: Supabase-API (wenn JWT_SECRET nicht gesetzt)
        try:
            resp = supabase.auth.get_user(token)
            user = resp.user if resp else None
        except Exception as e:
            logging.error(f"JWT validation error: {e}")
            return None

    if user:
        if len(_jwt_cache) >= _JWT_CACHE_MAX:
            oldest = min(_jwt_cache, key=lambda k: _jwt_cache[k][1])
            del _jwt_cache[oldest]
        _jwt_cache[cache_key] = (user, now + _JWT_CACHE_TTL)

    return user


@app.route('/verify', methods=['GET'])
@limiter.limit("600 per minute")
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


_BACKUP_SOURCES = [
    'n8n/backup/workflows',
    'docker-compose.yml',
    'Caddyfile',
    '.env.example',
    'auth-gateway/app.py',
    'auth-gateway/requirements.txt',
    'dashboard/index.html',
    'dashboard/style.css',
    'dashboard/auth.js',
    'dashboard/health.js',
    'dashboard/admin.js',
    'backup/backup-daemon.sh',
    'backup/backup.sh',
]


@app.route('/control/backup', methods=['POST'])
def trigger_backup():
    """Erstellt ein Backup direkt in Python – kein externer Daemon nötig."""
    user = _get_verified_user()
    if not user:
        logging.warning("Unauthorized backup trigger attempt.")
        return jsonify({"error": "Unauthorized"}), 401

    try:
        os.makedirs(_BACKUP_DIR, exist_ok=True)

        from datetime import datetime
        ts = int(time.time())
        name = f"backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        archive_path = os.path.join(_BACKUP_DIR, f"{name}.tar.gz")
        meta_path = os.path.join(_BACKUP_DIR, f"{name}.meta.json")

        file_count = 0
        with tarfile.open(archive_path, 'w:gz') as tf:
            for rel_path in _BACKUP_SOURCES:
                full_path = os.path.join(_APP_DIR, rel_path)
                if not os.path.exists(full_path):
                    continue
                tf.add(full_path, arcname=rel_path, recursive=True,
                       filter=lambda m: None if any(
                           x in m.name for x in ['.pyc', '__pycache__', '.git']
                       ) else m)
                if os.path.isfile(full_path):
                    file_count += 1
                else:
                    file_count += sum(len(f) for _, _, f in os.walk(full_path))

        size = os.path.getsize(archive_path)

        with open(meta_path, 'w') as f:
            json.dump({"name": name, "timestamp": ts, "size": size, "files": file_count}, f)

        # Status-Datei aktualisieren
        with open(_BACKUP_STATUS, 'w') as f:
            f.write(f"success:{ts}")

        # Alte Backups bereinigen (max. 10 behalten)
        old_metas = sorted(glob.glob(os.path.join(_BACKUP_DIR, 'backup_*.meta.json')), reverse=True)
        for old_meta in old_metas[10:]:
            try:
                os.remove(old_meta)
                os.remove(old_meta.replace('.meta.json', '.tar.gz'))
            except Exception:
                pass

        logging.info(f"Backup erstellt von {user.id}: {name} ({file_count} Dateien, {size} B)")
        return jsonify({"status": "success", "backup": name, "files": file_count, "size": size}), 200

    except Exception as e:
        logging.error(f"Backup-Fehler: {e}")
        try:
            with open(_BACKUP_STATUS, 'w') as f:
                f.write(f"failed:{int(time.time())}")
        except Exception:
            pass
        return jsonify({"error": "Backup fehlgeschlagen"}), 500


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


# Sicherheits-Hilfsfunktionen für Backup-Endpoints
_BACKUP_NAME_RE = re.compile(r'^backup_\d{8}_\d{6}$')
_BACKUP_DIR = os.path.dirname(_BACKUP_TRIGGER)
# auth-gateway bekommt ./:/app:ro – damit kann diff aktuelle Dateien lesen
_APP_DIR = os.environ.get("APP_DIR", "/app")


def _validate_backup_name(name):
    """Gibt True zurück wenn der Backup-Name dem erwarteten Format entspricht."""
    return bool(name and _BACKUP_NAME_RE.match(name))


def _validate_filepath(filepath):
    """Gibt True zurück wenn der Dateipfad sicher ist (kein Path Traversal)."""
    if not filepath:
        return False
    if '..' in filepath:
        return False
    # Nur relative Pfade erlaubt, keine absoluten
    if filepath.startswith('/'):
        return False
    return True


@app.route('/control/backup/list', methods=['GET'])
def backup_list():
    """Listet alle verfügbaren Backups mit Metadaten. Auth erforderlich."""
    user = _get_verified_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        meta_files = glob.glob(os.path.join(_BACKUP_DIR, 'backup_*.meta.json'))
        meta_files.sort(reverse=True)  # Neueste zuerst

        backups = []
        for meta_path in meta_files:
            try:
                with open(meta_path, 'r') as f:
                    data = json.load(f)
                # Sicherstellen dass der Name dem Pattern entspricht
                name = data.get('name', '')
                if _validate_backup_name(name):
                    backups.append(data)
            except Exception:
                continue

        return jsonify(backups), 200
    except Exception as e:
        logging.error(f"backup_list error: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route('/control/backup/files', methods=['GET'])
def backup_files():
    """Listet alle Dateien in einem Backup-Archiv. Auth erforderlich."""
    user = _get_verified_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    backup_name = request.args.get('backup', '')
    if not _validate_backup_name(backup_name):
        return jsonify({"error": "Ungültiger Backup-Name"}), 400

    archive_path = os.path.join(_BACKUP_DIR, backup_name + '.tar.gz')
    if not os.path.isfile(archive_path):
        return jsonify({"error": "Backup nicht gefunden"}), 404

    try:
        files = []
        with tarfile.open(archive_path, 'r:gz') as tf:
            for member in tf.getmembers():
                if member.isfile():
                    files.append({
                        "path": member.name,
                        "size": member.size,
                    })
        return jsonify(files), 200
    except Exception as e:
        logging.error(f"backup_files error: {e}")
        return jsonify({"error": "Archiv konnte nicht gelesen werden"}), 500


@app.route('/control/backup/diff', methods=['GET'])
def backup_diff():
    """Vergleicht eine Datei aus dem Backup mit der aktuellen Version. Auth erforderlich."""
    user = _get_verified_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    backup_name = request.args.get('backup', '')
    filepath = request.args.get('file', '')

    if not _validate_backup_name(backup_name):
        return jsonify({"error": "Ungültiger Backup-Name"}), 400
    if not _validate_filepath(filepath):
        return jsonify({"error": "Ungültiger Dateipfad"}), 400

    archive_path = os.path.join(_BACKUP_DIR, backup_name + '.tar.gz')
    if not os.path.isfile(archive_path):
        return jsonify({"error": "Backup nicht gefunden"}), 404

    try:
        # Alte Version aus dem Archiv lesen
        old_lines = []
        with tarfile.open(archive_path, 'r:gz') as tf:
            try:
                member = tf.getmember(filepath)
                f = tf.extractfile(member)
                if f:
                    old_lines = f.read().decode('utf-8', errors='replace').splitlines(keepends=True)
            except KeyError:
                return jsonify({"error": "Datei nicht im Backup gefunden"}), 404

        # Aktuelle Version aus /app lesen
        current_path = os.path.join(_APP_DIR, filepath)
        # Sicherstellen dass wir nicht außerhalb von _APP_DIR lesen
        real_current = os.path.realpath(current_path)
        real_app = os.path.realpath(_APP_DIR)
        if not real_current.startswith(real_app + os.sep) and real_current != real_app:
            return jsonify({"error": "Ungültiger Dateipfad"}), 400

        new_lines = []
        if os.path.isfile(current_path):
            with open(current_path, 'r', errors='replace') as f:
                new_lines = f.readlines()

        # Unified Diff berechnen
        diff = list(difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile='backup/' + filepath,
            tofile='current/' + filepath,
            lineterm=''
        ))

        return jsonify({
            "diff": diff,
            "changed": len(diff) > 0,
            "file": filepath,
        }), 200
    except Exception as e:
        logging.error(f"backup_diff error: {e}")
        return jsonify({"error": "Diff konnte nicht erstellt werden"}), 500


@app.route('/control/restore', methods=['POST'])
def trigger_restore():
    """Schreibt einen Restore-Trigger, damit backup-daemon den Restore ausführt. Auth erforderlich."""
    user = _get_verified_user()
    if not user:
        logging.warning("Unauthorized restore attempt.")
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    backup_name = data.get('backup', '')

    if not _validate_backup_name(backup_name):
        return jsonify({"error": "Ungültiger Backup-Name"}), 400

    archive_path = os.path.join(_BACKUP_DIR, backup_name + '.tar.gz')
    if not os.path.isfile(archive_path):
        return jsonify({"error": "Backup nicht gefunden"}), 404

    restore_trigger = os.path.join(_BACKUP_DIR, '.restore')
    try:
        with open(restore_trigger, 'w') as f:
            f.write(backup_name + '\n')
        logging.info(f"Restore triggered by user {user.id}: {backup_name}")
        return jsonify({"status": "triggered", "backup": backup_name}), 200
    except Exception as e:
        logging.error(f"trigger_restore error: {e}")
        return jsonify({"error": "Internal server error"}), 500
