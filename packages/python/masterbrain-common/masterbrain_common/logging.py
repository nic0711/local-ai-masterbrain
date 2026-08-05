"""Strukturiertes JSON-Logging mit request-scoped Correlation-ID."""
from __future__ import annotations

import contextvars
import logging
import uuid

from pythonjsonlogger import json as jsonlogger

_correlation_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id", default="-"
)


def new_correlation_id() -> str:
    return uuid.uuid4().hex


def set_correlation_id(value: str) -> None:
    _correlation_id.set(value)


def get_correlation_id() -> str:
    return _correlation_id.get()


class _CorrelationIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id()
        return True


def configure_json_logging(service_name: str, level: int = logging.INFO) -> None:
    """Ersetzt die Handler des Root-Loggers durch einen einzelnen
    JSON-formatierenden Handler, der auf jedem Record die aktuelle
    Correlation-ID mitfuehrt."""
    handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(correlation_id)s %(message)s",
        rename_fields={"asctime": "timestamp", "levelname": "level", "name": "logger"},
    )
    handler.setFormatter(formatter)
    handler.addFilter(_CorrelationIdFilter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
    root.info("json logging configured", extra={"service": service_name})


def install_flask_correlation_id(app) -> None:
    """Registriert Flask before_request/after_request-Hooks: liest eine
    eingehende X-Correlation-ID oder erzeugt eine neue, macht sie fuer die
    Dauer des Requests ueber get_correlation_id() verfuegbar und spiegelt
    sie im Response-Header."""

    @app.before_request
    def _set_correlation_id():
        from flask import request

        incoming = request.headers.get("X-Correlation-ID")
        set_correlation_id(incoming or new_correlation_id())

    @app.after_request
    def _echo_correlation_id(response):
        response.headers["X-Correlation-ID"] = get_correlation_id()
        return response
