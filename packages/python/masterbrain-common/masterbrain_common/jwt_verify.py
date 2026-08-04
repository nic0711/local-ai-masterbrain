"""HS256-JWT-Verifikation mit In-Memory-TTL-Cache und RFC-7515-crit-Header-Pruefung.

Migriert aus auth-gateway/app.py (_verify_token_string). Haengt bewusst nicht
vom supabase-SDK ab - servicebezogene Fallback-Logik (z.B. Supabase-API-Aufruf
wenn kein Secret gesetzt ist) bleibt im jeweiligen Service.
"""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from typing import Optional

import jwt as pyjwt


@dataclass(frozen=True)
class VerifiedUser:
    id: str
    email: str
    aal: str


class JWTVerifier:
    """Verifiziert HS256-signierte JWTs gegen ein gemeinsames Secret, mit
    einem groessenbegrenzten In-Memory-Cache, um dasselbe Token nicht bei
    jedem Request erneut kryptografisch zu pruefen."""

    def __init__(
        self,
        secret: str,
        audience: str = "authenticated",
        cache_ttl: int = 300,
        cache_max: int = 500,
    ) -> None:
        self._secret = secret
        self._audience = audience
        self._cache_ttl = cache_ttl
        self._cache_max = cache_max
        self._cache: dict[str, tuple[VerifiedUser, float]] = {}

    def verify(self, token: str) -> Optional[VerifiedUser]:
        now = time.time()
        # SHA-256 des vollstaendigen Tokens als Cache-Key, um
        # Suffix-Kollisions-Angriffe zu vermeiden.
        cache_key = hashlib.sha256(token.encode()).hexdigest()

        cached = self._cache.get(cache_key)
        if cached:
            user, expires_at = cached
            if now < expires_at:
                return user
            del self._cache[cache_key]

        try:
            # RFC 7515 §4.1.11: Tokens mit unbekannten kritischen Extensions
            # muessen abgelehnt werden. PyJWT erzwingt das nicht selbst.
            unverified_header = pyjwt.get_unverified_header(token)
            if unverified_header.get("crit"):
                return None
            payload = pyjwt.decode(
                token, self._secret, algorithms=["HS256"], audience=self._audience,
            )
        except pyjwt.ExpiredSignatureError:
            return None
        except pyjwt.InvalidTokenError:
            return None

        token_exp = payload.get("exp")
        user = VerifiedUser(
            id=payload.get("sub", ""),
            email=payload.get("email", ""),
            aal=payload.get("aal", "aal1"),
        )

        if len(self._cache) >= self._cache_max:
            oldest = min(self._cache, key=lambda k: self._cache[k][1])
            del self._cache[oldest]
        expires_at = now + self._cache_ttl
        if token_exp:
            expires_at = min(expires_at, token_exp)
        self._cache[cache_key] = (user, expires_at)

        return user

    def clear_cache(self) -> None:
        """Leert den Verifikations-Cache vollstaendig (z.B. fuer Tests)."""
        self._cache.clear()
