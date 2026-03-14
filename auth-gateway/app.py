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
    "ocr-service":        ("ocr-service", 8002, "/health"),
    "supabase":           ("supabase-auth", 9999, "/health"),
    "minio":              ("localai-minio-1", 9000, "/minio/health/live"),
    "clickhouse":         ("clickhouse", 8123, "/ping"),
    "obsidian":           ("host.docker.internal", 27123, "/"),
    "uptime-kuma":        ("uptime-kuma", 3001, "/"),
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
    'dashboard/main.js',
    'dashboard/health.js',
    'dashboard/admin.js',
    'dashboard/entrypoint.sh',
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


_USER_ID_RE = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')


@app.route('/control/users', methods=['GET'])
def list_users():
    """Listet alle Benutzer. Auth + Admin erforderlich."""
    user = _get_verified_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    if not supabase:
        return jsonify({"error": "Auth service not configured"}), 500
    try:
        resp = supabase.auth.admin.list_users()
        users = []
        for u in resp:
            users.append({
                "id": u.id,
                "email": u.email,
                "created_at": u.created_at.isoformat() if hasattr(u.created_at, 'isoformat') else str(u.created_at or ''),
                "last_sign_in_at": u.last_sign_in_at.isoformat() if hasattr(u.last_sign_in_at, 'isoformat') else str(u.last_sign_in_at or ''),
            })
        return jsonify(users), 200
    except Exception as e:
        logging.error(f"list_users error: {e}")
        return jsonify({"error": "Fehler beim Laden der Benutzer"}), 500


@app.route('/control/users', methods=['POST'])
def create_user():
    """Legt einen neuen Benutzer an. Auth erforderlich."""
    user = _get_verified_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    if not supabase:
        return jsonify({"error": "Auth service not configured"}), 500
    data = request.get_json(silent=True) or {}
    email = data.get('email', '').strip()
    password = data.get('password', '')
    if not email or not password:
        return jsonify({"error": "Email und Passwort erforderlich"}), 400
    if len(password) < 8:
        return jsonify({"error": "Passwort muss mindestens 8 Zeichen haben"}), 400
    try:
        resp = supabase.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True,
        })
        return jsonify({"id": resp.user.id, "email": resp.user.email}), 201
    except Exception as e:
        logging.error(f"create_user error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/control/users/password', methods=['POST'])
def reset_user_password():
    """Setzt das Passwort eines Benutzers zurück. Auth erforderlich."""
    user = _get_verified_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    if not supabase:
        return jsonify({"error": "Auth service not configured"}), 500
    data = request.get_json(silent=True) or {}
    user_id = data.get('user_id', '')
    password = data.get('password', '')
    if not _USER_ID_RE.match(user_id):
        return jsonify({"error": "Ungültige Benutzer-ID"}), 400
    if len(password) < 8:
        return jsonify({"error": "Passwort muss mindestens 8 Zeichen haben"}), 400
    try:
        supabase.auth.admin.update_user_by_id(user_id, {"password": password})
        logging.info(f"Password reset by {user.id} for user {user_id}")
        return jsonify({"status": "updated"}), 200
    except Exception as e:
        logging.error(f"reset_password error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/control/users/delete', methods=['POST'])
def delete_user():
    """Löscht einen Benutzer. Auth erforderlich. Eigenes Konto kann nicht gelöscht werden."""
    user = _get_verified_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    if not supabase:
        return jsonify({"error": "Auth service not configured"}), 500
    data = request.get_json(silent=True) or {}
    user_id = data.get('user_id', '')
    if not _USER_ID_RE.match(user_id):
        return jsonify({"error": "Ungültige Benutzer-ID"}), 400
    if user.id == user_id:
        return jsonify({"error": "Eigenes Konto kann nicht gelöscht werden"}), 400
    try:
        supabase.auth.admin.delete_user(user_id)
        logging.info(f"User {user_id} deleted by {user.id}")
        return jsonify({"status": "deleted"}), 200
    except Exception as e:
        logging.error(f"delete_user error: {e}")
        return jsonify({"error": str(e)}), 500


# ── Service Control ──────────────────────────────────────────────────────────

# Allowlist: API-Key → Docker-Container-Name (nur steuerbare App-Dienste)
_CONTROLLABLE = {
    'n8n':                'n8n',
    'open-webui':         'open-webui',
    'flowise':            'flowise',
    'neo4j':              'neo4j',
    'qdrant':             'qdrant',
    'crawl4ai':           'crawl4ai',
    'searxng':            'searxng',
    'python-nlp-service': 'python-nlp-service',
    'langfuse-web':       'localai-langfuse-web-1',
    'langfuse-worker':    'localai-langfuse-worker-1',
    'minio':              'localai-minio-1',
    'clickhouse':         'localai-clickhouse-1',
    'redis':              'redis',
    'uptime-kuma':        'uptime-kuma',
}

_MACROS_FILE = os.environ.get("MACROS_FILE", "/opt/project/dashboard/macros.json")


def _get_docker_container(service_key):
    """Gibt den Docker-Container für einen erlaubten Service zurück oder None."""
    import docker as docker_sdk
    container_name = _CONTROLLABLE.get(service_key)
    if not container_name:
        return None, None
    client = docker_sdk.from_env()
    try:
        container = client.containers.get(container_name)
        return client, container
    except docker_sdk.errors.NotFound:
        return client, None


@app.route('/control/services/status', methods=['GET'])
@limiter.limit("30 per minute")
def docker_service_status():
    """Docker-basierter Container-Status für alle steuerbaren Dienste. Auth erforderlich."""
    user = _get_verified_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    import docker as docker_sdk
    try:
        client = docker_sdk.from_env()
        result = {}
        for key, container_name in _CONTROLLABLE.items():
            try:
                container = client.containers.get(container_name)
                result[key] = 'up' if container.status == 'running' else 'down'
            except docker_sdk.errors.NotFound:
                result[key] = 'down'
        return jsonify(result), 200
    except Exception as e:
        logging.error(f"docker_service_status error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/control/services/<service>/<action>', methods=['POST'])
@limiter.limit("10 per minute")
def service_control(service, action):
    """Startet, stoppt oder startet einen Container neu. Auth erforderlich."""
    user = _get_verified_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    if service not in _CONTROLLABLE:
        return jsonify({"error": f"Dienst '{service}' nicht erlaubt"}), 400

    if action not in ('start', 'stop', 'restart'):
        return jsonify({"error": f"Aktion '{action}' nicht erlaubt"}), 400

    try:
        import docker as docker_sdk
        client, container = _get_docker_container(service)
        if container is None:
            return jsonify({"error": f"Container für '{service}' nicht gefunden"}), 404

        if action == 'start':
            container.start()
        elif action == 'stop':
            container.stop(timeout=10)
        elif action == 'restart':
            container.restart(timeout=10)

        logging.info(f"[CONTROL] {user.id} → {action} {service}")
        return jsonify({"status": "ok", "message": f"{service} {action} ausgeführt"}), 200
    except Exception as e:
        logging.error(f"service_control error ({service}/{action}): {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/control/services/<service>/logs', methods=['GET'])
@limiter.limit("30 per minute")
def service_logs(service):
    """Gibt die letzten N Log-Zeilen eines Containers zurück. Auth erforderlich."""
    user = _get_verified_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    if service not in _CONTROLLABLE:
        return jsonify({"error": f"Dienst '{service}' nicht erlaubt"}), 400

    lines = request.args.get('lines', 50)
    try:
        lines = max(1, min(int(lines), 500))
    except (ValueError, TypeError):
        lines = 50

    try:
        _, container = _get_docker_container(service)
        if container is None:
            return jsonify({"error": f"Container für '{service}' nicht gefunden"}), 404

        raw = container.logs(tail=lines, timestamps=True)
        log_text = raw.decode('utf-8', errors='replace')
        logging.info(f"[CONTROL] {user.id} → logs {service} (tail={lines})")
        return jsonify({"service": service, "lines": lines, "logs": log_text}), 200
    except Exception as e:
        logging.error(f"service_logs error ({service}): {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/control/macros', methods=['GET'])
@limiter.limit("30 per minute")
def list_macros():
    """Gibt die Macro-Definitionen zurück. Auth erforderlich."""
    user = _get_verified_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        with open(_MACROS_FILE, 'r') as f:
            data = json.load(f)
        return jsonify(data), 200
    except FileNotFoundError:
        return jsonify({"macros": []}), 200
    except Exception as e:
        logging.error(f"list_macros error: {e}")
        return jsonify({"error": "Macros konnten nicht geladen werden"}), 500


@app.route('/control/macro/<macro_id>', methods=['POST'])
@limiter.limit("5 per minute")
def run_macro(macro_id):
    """Führt ein vordefiniertes Macro aus. Auth erforderlich."""
    user = _get_verified_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        with open(_MACROS_FILE, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        return jsonify({"error": "Macros-Datei nicht gefunden"}), 404
    except Exception as e:
        return jsonify({"error": "Macros konnten nicht geladen werden"}), 500

    macro = next((m for m in data.get('macros', []) if m.get('id') == macro_id), None)
    if not macro:
        return jsonify({"error": f"Macro '{macro_id}' nicht gefunden"}), 404

    results = []
    errors = []
    for step in macro.get('actions', []):
        svc = step.get('service', '')
        act = step.get('action', '')

        if svc not in _CONTROLLABLE or act not in ('start', 'stop', 'restart'):
            errors.append(f"Übersprungen: {act} {svc} (nicht erlaubt)")
            continue

        try:
            import docker as docker_sdk
            _, container = _get_docker_container(svc)
            if container is None:
                errors.append(f"{svc}: Container nicht gefunden")
                continue
            if act == 'start':
                container.start()
            elif act == 'stop':
                container.stop(timeout=10)
            elif act == 'restart':
                container.restart(timeout=10)
            results.append(f"{act} {svc}: ok")
            logging.info(f"[CONTROL] macro={macro_id} {user.id} → {act} {svc}")
        except Exception as e:
            errors.append(f"{act} {svc}: {e}")
            logging.error(f"run_macro error ({macro_id} {act} {svc}): {e}")

    return jsonify({
        "status": "ok" if not errors else "partial",
        "macro": macro_id,
        "results": results,
        "errors": errors,
    }), 200


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
