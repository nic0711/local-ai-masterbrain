"""Strukturiertes Audit-Logging fuer sicherheitsrelevante Aktionen.

Das reine Vorhandensein dieses Moduls ist keine Schutzmassnahme - es muss
tatsaechlich an den sicherheitsrelevanten Stellen aufgerufen werden (siehe
auth-gateway/app.py: service_control(), service_logs(), run_macro()).
"""
from __future__ import annotations

import logging
import time

_audit_logger = logging.getLogger("audit")


def log_event(actor: str, action: str, target: str, result: str, **extra) -> None:
    """Emittiert einen strukturierten Audit-Log-Eintrag. `result` sollte
    'ok', 'error' oder ein spezifischerer Ergebnis-String sein."""
    _audit_logger.info(
        "audit_event",
        extra={
            "audit": True,
            "actor": actor,
            "action": action,
            "target": target,
            "result": result,
            "audit_timestamp": time.time(),
            **extra,
        },
    )
