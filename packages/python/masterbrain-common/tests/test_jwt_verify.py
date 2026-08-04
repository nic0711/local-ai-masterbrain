"""Regressionstests fuer masterbrain_common.jwt_verify, portiert aus den
urspruenglichen auth-gateway/tests/test_app.py-Faellen fuer _verify_token_string."""
import time

import jwt as pyjwt
import pytest

from masterbrain_common.jwt_verify import JWTVerifier

_SECRET = "test-secret-key-for-unit-tests"
_USER_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
_EMAIL = "test@example.com"


def _make_token(secret=_SECRET, sub=_USER_ID, email=_EMAIL, exp_offset=3600,
                 extra_header=None, aud="authenticated", aal="aal2"):
    payload = {
        "sub": sub,
        "email": email,
        "aud": aud,
        "aal": aal,
        "iat": int(time.time()),
        "exp": int(time.time()) + exp_offset,
    }
    return pyjwt.encode(payload, secret, algorithm="HS256", headers=extra_header or {})


@pytest.fixture()
def verifier():
    return JWTVerifier(secret=_SECRET)


def test_valid_token_verified(verifier):
    token = _make_token()
    user = verifier.verify(token)
    assert user is not None
    assert user.id == _USER_ID
    assert user.email == _EMAIL
    assert user.aal == "aal2"


def test_expired_token_rejected(verifier):
    token = _make_token(exp_offset=-3600)
    assert verifier.verify(token) is None


def test_wrong_secret_rejected(verifier):
    token = _make_token(secret="wrong-secret")
    assert verifier.verify(token) is None


def test_malformed_token_rejected(verifier):
    assert verifier.verify("not.a.jwt") is None


def test_crit_header_rejected(verifier):
    """RFC 7515 §4.1.11: Tokens mit 'crit'-Header muessen abgelehnt werden."""
    token = _make_token(extra_header={"crit": ["exp"]})
    assert verifier.verify(token) is None


def test_wrong_audience_rejected(verifier):
    token = _make_token(aud="something-else")
    assert verifier.verify(token) is None


def test_cache_returns_same_user_without_reverification(verifier):
    token = _make_token()
    first = verifier.verify(token)
    # Sekundaerer Aufruf muss aus dem Cache bedient werden (gleiche Identitaet).
    second = verifier.verify(token)
    assert first == second


def test_cache_not_extended_past_token_exp(verifier):
    """Der Cache darf ein Token nicht ueber sein echtes exp hinaus akzeptieren,
    auch wenn die TTL des Caches laenger waere."""
    token = _make_token(exp_offset=30)
    assert verifier.verify(token) is not None
    import hashlib

    key = hashlib.sha256(token.encode()).hexdigest()
    _user, expires_at = verifier._cache[key]
    assert expires_at <= int(time.time()) + 31


def test_cache_eviction_at_max_capacity():
    v = JWTVerifier(secret=_SECRET, cache_max=2)
    tokens = [_make_token(sub=f"user-{i}") for i in range(3)]
    for t in tokens:
        v.verify(t)
    assert len(v._cache) <= 2


def test_clear_cache_empties_cache(verifier):
    verifier.verify(_make_token())
    assert len(verifier._cache) == 1
    verifier.clear_cache()
    assert len(verifier._cache) == 0
