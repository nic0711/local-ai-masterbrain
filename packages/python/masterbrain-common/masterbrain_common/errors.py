"""Einheitliches Fehler-JSON-Format."""
from __future__ import annotations


def error_response(message: str, code: str = "error") -> dict:
    return {"error": message, "code": code}
