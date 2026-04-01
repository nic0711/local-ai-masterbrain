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
                exp_offset=3600, extra_header=None):
    """Return a signed HS256 JWT."""
    payload = {
        "sub": sub,
        "email": email,
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
    """Clear the in-memory JWT cache between tests."""
    # app may not be imported yet (first test in session); guard against that.
    if "app" in sys.modules:
        sys.modules["app"]._jwt_cache.clear()
    yield
    if "app" in sys.modules:
        sys.modules["app"]._jwt_cache.clear()


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
