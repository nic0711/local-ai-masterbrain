"""Health/Ready/Version-Response-Helper.

Kein /metrics in dieser Version (siehe README.md - bewusst nicht enthalten,
kein konkreter Verwendungszweck in Phase 2A).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass
class ReadyCheck:
    name: str
    check: Callable[[], bool]


def health_response() -> tuple[dict, int]:
    """Minimale, abhaengigkeitsfreie Liveness-Antwort. Darf NIEMALS externe
    Services aufrufen - dient als Ziel fuer den Docker-HEALTHCHECK, der bei
    kurzzeitig nicht erreichbaren Abhaengigkeiten sonst in eine
    Restart-Schleife laufen wuerde."""
    return {"status": "ok"}, 200


def ready_response(checks: list[ReadyCheck]) -> tuple[dict, int]:
    """Fuehrt jede Abhaengigkeitspruefung aus und meldet die Gesamt-Readiness.
    Fuer einen eigenen /ready-Endpoint gedacht, NIEMALS fuer den
    Docker-HEALTHCHECK (externe Abhaengigkeiten duerfen keine
    Container-Restart-Schleife ausloesen)."""
    results: dict[str, str] = {}
    all_ok = True
    for c in checks:
        try:
            ok = bool(c.check())
        except Exception:
            ok = False
        results[c.name] = "ok" if ok else "down"
        all_ok = all_ok and ok
    status_code = 200 if all_ok else 503
    return {"status": "ready" if all_ok else "not_ready", "checks": results}, status_code


def version_response(
    service_name: str, service_version: str, common_version: str, git_commit: str
) -> tuple[dict, int]:
    """Keine Secrets, keine internen Pfade - nur Versions-/Commit-Metadaten."""
    return {
        "service": service_name,
        "service_version": service_version,
        "masterbrain_common_version": common_version,
        "git_commit": git_commit,
    }, 200
