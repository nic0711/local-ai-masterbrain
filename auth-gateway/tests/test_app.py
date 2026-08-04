"""
Security-focused tests for auth-gateway/app.py.

External dependencies (Supabase, Docker) are mocked via unittest.mock so that
tests run without any live services.
"""
import importlib
import json
import os
import sys
import time
import hashlib
import tempfile
import tarfile
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, mock_open

import jwt as pyjwt
import pytest


# ---------------------------------------------------------------------------
# Helpers to build a signed JWT for tests
# ---------------------------------------------------------------------------
_TEST_SECRET = "test-secret-key-for-unit-tests"
_TEST_USER_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
_TEST_EMAIL = "test@example.com"


def _make_token(secret=_TEST_SECRET, sub=_TEST_USER_ID, email=_TEST_EMAIL,
                exp_offset=3600, extra_header=None, aud="authenticated", aal="aal2"):
    """Return a signed HS256 JWT. Default aal2 (MFA abgeschlossen)."""
    payload = {
        "sub": sub,
        "email": email,
        "aud": aud,
        "aal": aal,
        "iat": int(time.time()),
        "exp": int(time.time()) + exp_offset,
    }
    headers = extra_header or {}
    return pyjwt.encode(payload, secret, algorithm="HS256", headers=headers)


def _expired_token():
    return _make_token(exp_offset=-3600)


# ---------------------------------------------------------------------------
# Fixture: Flask test client with Supabase mocked out
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def reset_jwt_cache():
    """Clear the in-memory JWT cache (masterbrain_common.jwt_verify.JWTVerifier)
    between tests."""
    # app may not be imported yet (first test in session); guard against that.
    if "app" in sys.modules and sys.modules["app"]._jwt_verifier:
        sys.modules["app"]._jwt_verifier.clear_cache()
    yield
    if "app" in sys.modules and sys.modules["app"]._jwt_verifier:
        sys.modules["app"]._jwt_verifier.clear_cache()


@pytest.fixture()
def client(tmp_path):
    """
    Create a Flask test client.

    - Supabase is replaced with a MagicMock.
    - JWT_SECRET is set to _TEST_SECRET so local verification works.
    - Backup paths are redirected to a temp directory.
    """
    env_patch = {
        "SUPABASE_URL": "http://fake-supabase",
        "SUPABASE_SERVICE_ROLE_KEY": "fake-key",
        "JWT_SECRET": _TEST_SECRET,
        "BACKUP_TRIGGER_FILE": str(tmp_path / ".trigger"),
        "BACKUP_STATUS_FILE": str(tmp_path / ".backup_status"),
        "APP_DIR": str(tmp_path),
        # Fail-closed RBAC: Default-Testnutzer explizit als Superadmin autorisieren,
        # damit die Admin-/Superadmin-Endpoint-Tests weiterhin gültig sind.
        "SUPERADMIN_EMAILS": _TEST_EMAIL,
    }

    # Patch env before importing the module
    with patch.dict(os.environ, env_patch):
        # Patch supabase.create_client so no real network call is made
        mock_supabase = MagicMock()
        with patch("supabase.create_client", return_value=mock_supabase):
            # Force a fresh import of app so env vars are picked up
            if "app" in sys.modules:
                del sys.modules["app"]
            import app as app_module

            app_module.supabase = mock_supabase
            app_module._JWT_SECRET = _TEST_SECRET
            app_module._BACKUP_TRIGGER = str(tmp_path / ".trigger")
            app_module._BACKUP_STATUS = str(tmp_path / ".backup_status")
            app_module._BACKUP_DIR = str(tmp_path)
            app_module._APP_DIR = str(tmp_path)

            app_module.app.config["TESTING"] = True
            # Disable rate limiting for unit tests
            app_module.limiter.enabled = False

            with app_module.app.test_client() as c:
                c._app_module = app_module
                yield c


# ---------------------------------------------------------------------------
# Fixtures für Superadmin-Tests
# ---------------------------------------------------------------------------

_SUPERADMIN_EMAIL = "superadmin@example.com"
_ADMIN_ONLY_EMAIL = "admin@example.com"

@pytest.fixture()
def client_with_roles(tmp_path):
    """Client mit SUPERADMIN_EMAILS und ADMIN_EMAILS gesetzt."""
    env_patch = {
        "SUPABASE_URL": "http://fake-supabase",
        "SUPABASE_SERVICE_ROLE_KEY": "fake-key",
        "JWT_SECRET": _TEST_SECRET,
        "BACKUP_TRIGGER_FILE": str(tmp_path / ".trigger"),
        "BACKUP_STATUS_FILE": str(tmp_path / ".backup_status"),
        "APP_DIR": str(tmp_path),
        "SUPERADMIN_EMAILS": _SUPERADMIN_EMAIL,
        "ADMIN_EMAILS": _ADMIN_ONLY_EMAIL,
    }
    with patch.dict(os.environ, env_patch):
        mock_supabase = MagicMock()
        with patch("supabase.create_client", return_value=mock_supabase):
            if "app" in sys.modules:
                del sys.modules["app"]
            import app as app_module

            app_module.supabase = mock_supabase
            app_module._JWT_SECRET = _TEST_SECRET
            app_module._BACKUP_TRIGGER = str(tmp_path / ".trigger")
            app_module._BACKUP_STATUS = str(tmp_path / ".backup_status")
            app_module._BACKUP_DIR = str(tmp_path)
            app_module._APP_DIR = str(tmp_path)
            app_module.app.config["TESTING"] = True
            app_module.limiter.enabled = False

            with app_module.app.test_client() as c:
                c._app_module = app_module
                yield c


# ---------------------------------------------------------------------------
# /verify endpoint
# ---------------------------------------------------------------------------

class TestVerifyEndpoint:
    def test_verify_valid_token_returns_200(self, client):
        token = _make_token()
        resp = client.get("/verify", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.data == b"OK"

    def test_verify_missing_token_returns_401(self, client):
        resp = client.get("/verify")
        assert resp.status_code == 401
        assert b"Unauthorized" in resp.data

    def test_verify_malformed_token_returns_401(self, client):
        resp = client.get("/verify", headers={"Authorization": "Bearer not.a.jwt"})
        assert resp.status_code == 401

    def test_verify_expired_token_returns_401(self, client):
        token = _expired_token()
        resp = client.get("/verify", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401

    def test_verify_wrong_secret_returns_401(self, client):
        token = _make_token(secret="wrong-secret")
        resp = client.get("/verify", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401

    def test_verify_crit_header_rejected(self, client):
        """RFC 7515 §4.1.11: tokens with 'crit' header must be rejected."""
        token = _make_token(extra_header={"crit": ["exp"]})
        resp = client.get("/verify", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401

    def test_verify_cookie_auth(self, client):
        """Token in cookie sb-access-token should also be accepted."""
        token = _make_token()
        client.set_cookie("sb-access-token", token)
        resp = client.get("/verify")
        assert resp.status_code == 200

    def test_verify_algorithm_confusion_none_rejected(self, client):
        """alg=none tokens must NOT be accepted (PyJWT rejects them by default)."""
        # Craft a token with alg=none manually
        import base64
        header = base64.urlsafe_b64encode(b'{"alg":"none","typ":"JWT"}').rstrip(b"=").decode()
        payload = base64.urlsafe_b64encode(
            json.dumps({"sub": _TEST_USER_ID, "exp": int(time.time()) + 3600}).encode()
        ).rstrip(b"=").decode()
        token = f"{header}.{payload}."
        resp = client.get("/verify", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401

    def test_verify_aal1_token_rejected(self, client):
        """MFA-Pflicht: ein reines Passwort-Token (aal1) darf /verify nicht passieren."""
        token = _make_token(aal="aal1")
        resp = client.get("/verify", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401
        assert b"MFA required" in resp.data

    def test_verify_aal2_token_accepted(self, client):
        """aal2-Token (Passwort + TOTP) wird akzeptiert."""
        token = _make_token(aal="aal2")
        resp = client.get("/verify", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_verify_missing_aal_treated_as_aal1(self, client):
        """Fehlt der aal-Claim, gilt der Default aal1 → abgelehnt."""
        import jwt as pyjwt
        payload = {
            "sub": _TEST_USER_ID, "email": _TEST_EMAIL, "aud": "authenticated",
            "iat": int(time.time()), "exp": int(time.time()) + 3600,
        }
        token = pyjwt.encode(payload, _TEST_SECRET, algorithm="HS256")
        resp = client.get("/verify", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# /session, /session/logout (F1: HttpOnly-Session-Cookie)
# ---------------------------------------------------------------------------

class TestSessionEndpoint:
    def test_session_valid_token_sets_httponly_cookie(self, client):
        token = _make_token()
        resp = client.post("/session", json={"access_token": token})
        assert resp.status_code == 200
        set_cookie = resp.headers.get("Set-Cookie", "")
        assert "sb-access-token=" in set_cookie
        assert "HttpOnly" in set_cookie
        assert "Secure" in set_cookie

    def test_session_missing_token_returns_400(self, client):
        resp = client.post("/session", json={})
        assert resp.status_code == 400

    def test_session_invalid_token_returns_401(self, client):
        resp = client.post("/session", json={"access_token": "not.a.jwt"})
        assert resp.status_code == 401

    def test_session_aal1_token_rejected(self, client):
        """MFA-Pflicht gilt auch für den Session-Endpoint."""
        token = _make_token(aal="aal1")
        resp = client.post("/session", json={"access_token": token})
        assert resp.status_code == 401

    def test_session_logout_clears_cookie(self, client):
        resp = client.post("/session/logout")
        assert resp.status_code == 200
        set_cookie = resp.headers.get("Set-Cookie", "")
        assert "sb-access-token=" in set_cookie
        assert "HttpOnly" in set_cookie


# ---------------------------------------------------------------------------
# /control/backup – POST (trigger backup)
# ---------------------------------------------------------------------------

class TestTriggerBackup:
    def test_backup_requires_auth(self, client):
        resp = client.post("/control/backup")
        assert resp.status_code == 401

    def test_backup_with_valid_token_succeeds(self, client, tmp_path):
        token = _make_token()
        resp = client.post(
            "/control/backup",
            headers={"Authorization": f"Bearer {token}"},
        )
        # The backup will fail because _APP_DIR is tmp_path and sources don't exist,
        # but auth must pass (we expect 200 or 500, not 401).
        assert resp.status_code != 401

    def test_backup_status_requires_auth(self, client):
        resp = client.get("/control/backup/status")
        assert resp.status_code == 401

    def test_backup_status_with_valid_token(self, client, tmp_path):
        # Write a fake status file
        status_file = tmp_path / ".backup_status"
        status_file.write_text("success:1700000000")
        token = _make_token()
        resp = client.get(
            "/control/backup/status",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        assert data["timestamp"] == 1700000000


# ---------------------------------------------------------------------------
# /control/backup/list, /files, /diff – name validation
# ---------------------------------------------------------------------------

class TestBackupNameValidation:
    def _auth_header(self):
        return {"Authorization": f"Bearer {_make_token()}"}

    def test_backup_list_requires_auth(self, client):
        resp = client.get("/control/backup/list")
        assert resp.status_code == 401

    def test_backup_files_invalid_name_rejected(self, client):
        resp = client.get(
            "/control/backup/files?backup=../../etc/passwd",
            headers=self._auth_header(),
        )
        assert resp.status_code == 400

    def test_backup_files_name_with_null_byte_rejected(self, client):
        resp = client.get(
            "/control/backup/files?backup=backup_20240101_120000\x00evil",
            headers=self._auth_header(),
        )
        assert resp.status_code in (400, 404)

    def test_backup_files_valid_name_not_found(self, client):
        resp = client.get(
            "/control/backup/files?backup=backup_20240101_120000",
            headers=self._auth_header(),
        )
        assert resp.status_code == 404

    def test_backup_diff_invalid_backup_name(self, client):
        resp = client.get(
            "/control/backup/diff?backup=INVALID&file=app.py",
            headers=self._auth_header(),
        )
        assert resp.status_code == 400

    def test_backup_diff_path_traversal_in_file_param(self, client):
        resp = client.get(
            "/control/backup/diff?backup=backup_20240101_120000&file=../../etc/passwd",
            headers=self._auth_header(),
        )
        assert resp.status_code == 400

    def test_backup_diff_absolute_path_in_file_param(self, client):
        resp = client.get(
            "/control/backup/diff?backup=backup_20240101_120000&file=/etc/passwd",
            headers=self._auth_header(),
        )
        assert resp.status_code == 400

    def test_backup_diff_valid_params_backup_not_found(self, client):
        resp = client.get(
            "/control/backup/diff?backup=backup_20240101_120000&file=auth-gateway/app.py",
            headers=self._auth_header(),
        )
        assert resp.status_code == 404

    def test_backup_files_tar_path_traversal_filtered(self, client, tmp_path):
        """Tar archive members with path-traversal names must be skipped."""
        archive_path = tmp_path / "backup_20240101_120000.tar.gz"
        with tarfile.open(str(archive_path), "w:gz") as tf:
            # Add a legitimate file
            legit = tmp_path / "legit.txt"
            legit.write_text("hello")
            tf.add(str(legit), arcname="auth-gateway/app.py")
            # Manually inject a TarInfo with a traversal path
            import io
            evil_info = tarfile.TarInfo(name="../../evil.txt")
            evil_data = b"pwned"
            evil_info.size = len(evil_data)
            tf.addfile(evil_info, io.BytesIO(evil_data))

        token = _make_token()
        resp = client.get(
            "/control/backup/files?backup=backup_20240101_120000",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        paths = [f["path"] for f in resp.get_json()]
        # The traversal path must NOT appear in the listing
        assert "../../evil.txt" not in paths
        assert "auth-gateway/app.py" in paths


# ---------------------------------------------------------------------------
# /control/services/:service/:action – allowlist enforcement
# ---------------------------------------------------------------------------

class TestServiceControl:
    def _auth_header(self):
        return {"Authorization": f"Bearer {_make_token()}"}

    def test_service_control_requires_auth(self, client):
        resp = client.post("/control/services/n8n/restart")
        assert resp.status_code == 401

    def test_service_control_unknown_service_rejected(self, client):
        resp = client.post(
            "/control/services/auth-gateway/restart",
            headers=self._auth_header(),
        )
        assert resp.status_code == 400
        data = resp.get_json()
        # Error must NOT echo back the potentially malicious service name
        assert "auth-gateway" not in data.get("error", "")

    def test_service_control_invalid_action_rejected(self, client):
        resp = client.post(
            "/control/services/n8n/exec",
            headers=self._auth_header(),
        )
        assert resp.status_code == 400
        data = resp.get_json()
        # Error must NOT echo back the action name
        assert "exec" not in data.get("error", "")

    def test_service_control_path_traversal_service_rejected(self, client):
        resp = client.post(
            "/control/services/../auth-gateway/restart",
            headers=self._auth_header(),
        )
        # Flask routing normalises this – should result in 404 or 400, never 200
        assert resp.status_code in (400, 404)

    @patch("app._get_docker_container")
    def test_service_control_start_allowed_service(self, mock_gdc, client):
        mock_container = MagicMock()
        mock_gdc.return_value = (MagicMock(), mock_container)
        resp = client.post(
            "/control/services/n8n/start",
            headers=self._auth_header(),
        )
        assert resp.status_code == 200
        mock_container.start.assert_called_once()

    @patch("app._get_docker_container")
    def test_service_control_stop_calls_timeout(self, mock_gdc, client):
        mock_container = MagicMock()
        mock_gdc.return_value = (MagicMock(), mock_container)
        resp = client.post(
            "/control/services/n8n/stop",
            headers=self._auth_header(),
        )
        assert resp.status_code == 200
        mock_container.stop.assert_called_once_with(timeout=10)

    @patch("app._get_docker_container")
    def test_service_control_docker_error_does_not_leak(self, mock_gdc, client):
        """Docker exception details must not appear in the response body."""
        mock_gdc.return_value = (MagicMock(), MagicMock())
        mock_gdc.return_value[1].restart.side_effect = RuntimeError("socket /var/run/docker.sock: permission denied")
        resp = client.post(
            "/control/services/n8n/restart",
            headers=self._auth_header(),
        )
        assert resp.status_code == 500
        body = resp.get_json()
        assert "permission denied" not in body.get("error", "")
        assert "docker.sock" not in body.get("error", "")

    @patch("app.subprocess.run")
    @patch("app._get_docker_container")
    def test_optional_service_start_uses_compose_when_container_absent(self, mock_gdc, mock_run, client):
        """Wenn ein optional-Service noch nicht als Container existiert, wird compose up aufgerufen."""
        mock_gdc.return_value = (MagicMock(), None)
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        resp = client.post(
            "/control/services/neo4j/start",
            headers=self._auth_header(),
        )
        assert resp.status_code == 200
        args = mock_run.call_args[0][0]
        assert "docker" in args[0]
        assert "compose" in args
        assert "--profile" in args
        assert "optional" in args
        assert "neo4j" in args

    @patch("app.subprocess.run")
    @patch("app._get_docker_container")
    def test_optional_service_compose_failure_returns_500(self, mock_gdc, mock_run, client):
        """Wenn compose up fehlschlägt, muss 500 zurückgegeben werden."""
        mock_gdc.return_value = (MagicMock(), None)
        mock_run.return_value = MagicMock(returncode=1, stderr="image not found")
        resp = client.post(
            "/control/services/flowise/start",
            headers=self._auth_header(),
        )
        assert resp.status_code == 500

    @patch("app._get_docker_container")
    def test_non_optional_service_not_found_returns_404(self, mock_gdc, client):
        """Nicht-optionale Services liefern 404 wenn Container fehlt."""
        mock_gdc.return_value = (MagicMock(), None)
        resp = client.post(
            "/control/services/n8n/start",
            headers=self._auth_header(),
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Superadmin-Rollentrennung
# ---------------------------------------------------------------------------

class TestSuperadminRole:
    """Superadmin-only Endpoints müssen Admin-Token mit 403 ablehnen."""

    def _superadmin_token(self):
        return _make_token(email=_SUPERADMIN_EMAIL)

    def _admin_token(self):
        return _make_token(email=_ADMIN_ONLY_EMAIL)

    def test_restore_requires_superadmin_not_admin(self, client_with_roles, tmp_path):
        """Admin-Token darf /control/restore nicht ausführen."""
        token = self._admin_token()
        resp = client_with_roles.post(
            "/control/restore",
            headers={"Authorization": f"Bearer {token}"},
            json={"backup": "backup_20240101_120000"},
        )
        assert resp.status_code == 403

    def test_restore_allowed_for_superadmin(self, client_with_roles, tmp_path):
        """Superadmin-Token darf /control/restore ausführen (backup muss existieren)."""
        backup_dir = str(tmp_path)
        import app as app_module
        app_module._BACKUP_DIR = backup_dir
        # Archiv anlegen damit 404 nicht aus "nicht gefunden" kommt
        import tarfile, os
        archive = os.path.join(backup_dir, "backup_20240101_120000.tar.gz")
        with tarfile.open(archive, "w:gz"):
            pass
        token = self._superadmin_token()
        resp = client_with_roles.post(
            "/control/restore",
            headers={"Authorization": f"Bearer {token}"},
            json={"backup": "backup_20240101_120000"},
        )
        assert resp.status_code == 200

    def test_list_users_requires_superadmin(self, client_with_roles):
        """Admin-Token darf /control/users nicht auflisten."""
        token = self._admin_token()
        resp = client_with_roles.get(
            "/control/users",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    def test_create_user_requires_superadmin(self, client_with_roles):
        """Admin-Token darf /control/users (POST) nicht aufrufen."""
        token = self._admin_token()
        resp = client_with_roles.post(
            "/control/users",
            headers={"Authorization": f"Bearer {token}"},
            json={"email": "new@example.com", "password": "secret123"},
        )
        assert resp.status_code == 403

    def test_delete_user_requires_superadmin(self, client_with_roles):
        """Admin-Token darf /control/users/delete nicht aufrufen."""
        token = self._admin_token()
        resp = client_with_roles.post(
            "/control/users/delete",
            headers={"Authorization": f"Bearer {token}"},
            json={"user_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"},
        )
        assert resp.status_code == 403

    def test_password_reset_requires_superadmin(self, client_with_roles):
        """Admin-Token darf /control/users/password nicht aufrufen."""
        token = self._admin_token()
        resp = client_with_roles.post(
            "/control/users/password",
            headers={"Authorization": f"Bearer {token}"},
            json={"user_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", "password": "newpass123"},
        )
        assert resp.status_code == 403

    def test_admin_can_still_control_services(self, client_with_roles):
        """Admin-Token darf weiterhin Service-Control aufrufen."""
        from unittest.mock import patch, MagicMock
        with patch("app._get_docker_container") as mock_gdc:
            mock_container = MagicMock()
            mock_gdc.return_value = (MagicMock(), mock_container)
            token = self._admin_token()
            resp = client_with_roles.post(
                "/control/services/n8n/restart",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200


# ---------------------------------------------------------------------------
# JWT cache collision – SHA-256 key prevents suffix-based collision
# ---------------------------------------------------------------------------

class TestJwtCacheKey:
    def test_different_tokens_with_same_suffix_are_distinct(self, client):
        """
        Two tokens that share the same last 32 characters but have different
        payloads must not collide in the cache (old code used token[-32:]).
        """
        import app as app_module

        # Build two tokens that genuinely differ in their payload
        token_a = _make_token(sub="user-aaa")
        token_b = _make_token(sub="user-bbb")

        # Verify both independently
        with app_module.app.test_request_context(
            "/verify",
            headers={"Authorization": f"Bearer {token_a}"},
        ):
            user_a = app_module._get_verified_user()

        with app_module.app.test_request_context(
            "/verify",
            headers={"Authorization": f"Bearer {token_b}"},
        ):
            user_b = app_module._get_verified_user()

        assert user_a.id == "user-aaa"
        assert user_b.id == "user-bbb"


# ---------------------------------------------------------------------------
# /validate_filepath helper
# ---------------------------------------------------------------------------

class TestValidateFilepath:
    def _vf(self, path):
        import app as app_module
        return app_module._validate_filepath(path)

    def test_empty_path_rejected(self):
        assert self._vf("") is False

    def test_absolute_path_rejected(self):
        assert self._vf("/etc/passwd") is False

    def test_dotdot_rejected(self):
        assert self._vf("../../etc/passwd") is False

    def test_single_dotdot_rejected(self):
        assert self._vf("../secret") is False

    def test_valid_relative_path(self):
        assert self._vf("auth-gateway/app.py") is True

    def test_simple_filename(self):
        assert self._vf("app.py") is True


# ---------------------------------------------------------------------------
# Fail-closed RBAC & MFA (aal2) enforcement
# ---------------------------------------------------------------------------

class TestFailClosedRbac:
    def test_unlisted_user_denied_admin_endpoint(self, client_with_roles):
        """Ein Token, dessen E-Mail in KEINER Liste steht, wird auf Admin-Endpoints abgelehnt."""
        token = _make_token(email="nobody@example.com")
        resp = client_with_roles.post(
            "/control/services/n8n/restart",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    def test_aal1_denied_on_admin_endpoint(self, client):
        """aal1-Token (nur Passwort) darf keine Admin-Aktion auslösen, auch als Superadmin."""
        token = _make_token(aal="aal1")
        resp = client.post(
            "/control/backup",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code in (401, 403)


class TestMfaReset:
    def test_mfa_reset_requires_superadmin(self, client_with_roles):
        """Admin-Token darf /control/users/mfa-reset nicht aufrufen."""
        token = _make_token(email=_ADMIN_ONLY_EMAIL)
        resp = client_with_roles.post(
            "/control/users/mfa-reset",
            headers={"Authorization": f"Bearer {token}"},
            json={"user_id": _TEST_USER_ID},
        )
        assert resp.status_code == 403

    def test_mfa_reset_invalid_user_id(self, client_with_roles):
        """Ungültige user_id → 400."""
        token = _make_token(email=_SUPERADMIN_EMAIL)
        resp = client_with_roles.post(
            "/control/users/mfa-reset",
            headers={"Authorization": f"Bearer {token}"},
            json={"user_id": "not-a-uuid"},
        )
        assert resp.status_code == 400

    def test_mfa_reset_superadmin_removes_factors(self, client_with_roles):
        """Superadmin entfernt die Faktoren des Users über die GoTrue-Admin-API."""
        token = _make_token(email=_SUPERADMIN_EMAIL)
        fake_get = MagicMock()
        fake_get.raise_for_status.return_value = None
        fake_get.json.return_value = {"factors": [{"id": "factor-1"}, {"id": "factor-2"}]}
        with patch("httpx.get", return_value=fake_get) as mg, patch("httpx.delete") as md:
            resp = client_with_roles.post(
                "/control/users/mfa-reset",
                headers={"Authorization": f"Bearer {token}"},
                json={"user_id": _TEST_USER_ID},
            )
        assert resp.status_code == 200
        assert resp.get_json()["removed"] == 2
        assert md.call_count == 2


class TestJwtCacheExpiryCap:
    def test_cache_not_extended_past_token_exp(self, client):
        """Der Cache darf ein Token nicht über sein echtes exp hinaus akzeptieren."""
        import app as app_module
        token = _make_token(exp_offset=30)  # läuft in 30s ab
        with app_module.app.test_request_context(
            "/verify", headers={"Authorization": f"Bearer {token}"},
        ):
            assert app_module._get_verified_user() is not None
        # Cache-Eintrag darf nicht länger als das Token gelten
        # (Cache lebt jetzt in masterbrain_common.jwt_verify.JWTVerifier)
        import hashlib, time as _t
        key = hashlib.sha256(token.encode()).hexdigest()
        _user, expires_at = app_module._jwt_verifier._cache[key]
        assert expires_at <= int(_t.time()) + 31


# ---------------------------------------------------------------------------
# /ready, /version – masterbrain_common.health-basierte Endpunkte (Phase 2A)
# ---------------------------------------------------------------------------

class TestReadyEndpoint:
    def test_ready_ok_when_supabase_initialized(self, client):
        resp = client.get("/ready")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "ready"
        assert data["checks"]["supabase"] == "ok"

    def test_ready_503_when_supabase_unavailable(self, client):
        import app as app_module
        with patch.object(app_module, "supabase", None):
            resp = client.get("/ready")
        assert resp.status_code == 503
        data = resp.get_json()
        assert data["status"] == "not_ready"
        assert data["checks"]["supabase"] == "down"

    def test_ready_requires_no_auth(self, client):
        """Ready-Endpoint ist wie /health unauthenticated erreichbar
        (Orchestrierungs-/Monitoring-Zweck)."""
        resp = client.get("/ready")
        assert resp.status_code in (200, 503)


class TestVersionEndpoint:
    def test_version_contains_expected_fields_no_secrets(self, client):
        resp = client.get("/version")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["service"] == "auth-gateway"
        assert "service_version" in data
        assert "masterbrain_common_version" in data
        assert "git_commit" in data
        # Keine Secrets/interne Pfade in der Antwort
        body_text = resp.get_data(as_text=True)
        assert "JWT_SECRET" not in body_text
        assert "SUPABASE_SERVICE_ROLE_KEY" not in body_text


# ---------------------------------------------------------------------------
# Audit-Logging – tatsaechliche Verdrahtung, kein reines Vorhandensein
# ---------------------------------------------------------------------------

class TestAuditLogging:
    def _auth_header(self):
        return {"Authorization": f"Bearer {_make_token()}"}

    @patch("app.audit_log")
    @patch("app._get_docker_container")
    def test_service_control_start_emits_audit_event(self, mock_gdc, mock_audit, client):
        mock_container = MagicMock()
        mock_gdc.return_value = (MagicMock(), mock_container)
        resp = client.post("/control/services/n8n/start", headers=self._auth_header())
        assert resp.status_code == 200
        mock_audit.assert_called_once()
        _, kwargs = mock_audit.call_args
        assert kwargs["actor"] == _TEST_USER_ID
        assert kwargs["action"] == "start"
        assert kwargs["target"] == "n8n"
        assert kwargs["result"] == "ok"

    @patch("app.audit_log")
    @patch("app._get_docker_container")
    def test_service_control_error_emits_audit_event_with_error_result(
        self, mock_gdc, mock_audit, client
    ):
        mock_gdc.return_value = (MagicMock(), MagicMock())
        mock_gdc.return_value[1].restart.side_effect = RuntimeError("boom")
        resp = client.post("/control/services/n8n/restart", headers=self._auth_header())
        assert resp.status_code == 500
        mock_audit.assert_called_once()
        _, kwargs = mock_audit.call_args
        assert kwargs["result"] == "error"

    @patch("app.audit_log")
    @patch("app._get_docker_container")
    def test_service_logs_emits_audit_event(self, mock_gdc, mock_audit, client):
        mock_container = MagicMock()
        mock_container.logs.return_value = b"log line\n"
        mock_gdc.return_value = (MagicMock(), mock_container)
        resp = client.get("/control/services/n8n/logs", headers=self._auth_header())
        assert resp.status_code == 200
        mock_audit.assert_called_once()
        _, kwargs = mock_audit.call_args
        assert kwargs["action"] == "logs"
        assert kwargs["target"] == "n8n"
        assert kwargs["result"] == "ok"

    @patch("app.audit_log")
    @patch("app._get_docker_container")
    def test_run_macro_emits_audit_event_per_step(self, mock_gdc, mock_audit, client, tmp_path):
        import app as app_module

        mock_container = MagicMock()
        mock_gdc.return_value = (MagicMock(), mock_container)

        macros_file = tmp_path / "macros.json"
        macros_file.write_text(json.dumps({
            "macros": [
                {"id": "nightly", "actions": [{"service": "n8n", "action": "restart"}]}
            ]
        }))
        with patch.object(app_module, "_MACROS_FILE", str(macros_file)):
            resp = client.post("/control/macro/nightly", headers=self._auth_header())

        assert resp.status_code == 200
        mock_audit.assert_called_once()
        _, kwargs = mock_audit.call_args
        assert kwargs["action"] == "restart"
        assert kwargs["target"] == "n8n"
        assert kwargs["result"] == "ok"
        assert kwargs["macro_id"] == "nightly"
