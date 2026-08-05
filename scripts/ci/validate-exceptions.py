#!/usr/bin/env python3
"""Struktur-, Typ- und Ablaufpruefung fuer Security-Ausnahmedateien.

Prueft AUSSCHLIESSLICH Struktur, Ablaufdatum und Grundtyp einer Ausnahme
unter docs/planning/security-exceptions/*.yml. Diese Datei enthaelt KEIN
Freigabe-Feld - die eigentliche Freigabepruefung (echte GitHub-PR-Reviews auf
den aktuellen head_sha) uebernimmt scripts/ci/check-exception-approvals.py
zur Laufzeit, nicht ein Feld in der Ausnahmedatei selbst. Siehe
docs/handbook/09-verantwortlichkeiten.md fuer die Begruendung dieser
Trennung (vermeidet einen Freigabe-Deadlock durch Branch-Protection-bedingtes
Zuruecksetzen von Freigaben bei neuen Commits).
"""
from __future__ import annotations

import datetime
import glob
import sys

try:
    import yaml
except ImportError:
    print("FEHLER: PyYAML ist nicht installiert (pip install pyyaml).", file=sys.stderr)
    sys.exit(2)

REQUIRED_FIELDS = [
    "id",
    "finding_id",
    "component",
    "severity",
    "reason",
    "owner",
    "mitigation",
    "requested_by",
    "expires_on",
]

VALID_SEVERITIES = {"critical", "high"}

EXCEPTIONS_GLOB = "docs/planning/security-exceptions/*.yml"


def validate_file(path: str) -> list[str]:
    errors: list[str] = []
    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    for field in REQUIRED_FIELDS:
        if not data.get(field):
            errors.append(f"{path}: Pflichtfeld '{field}' fehlt oder ist leer")

    severity = str(data.get("severity", "")).lower()
    if severity not in VALID_SEVERITIES:
        errors.append(
            f"{path}: severity '{data.get('severity')}' ungueltig, erwartet 'critical' oder 'high'"
        )

    expires_on = data.get("expires_on")
    if expires_on:
        try:
            expiry_date = datetime.date.fromisoformat(str(expires_on))
        except ValueError:
            errors.append(f"{path}: 'expires_on' ist kein gueltiges ISO-8601-Datum")
        else:
            if expiry_date < datetime.date.today():
                errors.append(f"{path}: 'expires_on' ({expiry_date}) liegt in der Vergangenheit")

    return errors


def main() -> int:
    files = sorted(glob.glob(EXCEPTIONS_GLOB))
    if not files:
        print(f"Keine Ausnahmedateien unter {EXCEPTIONS_GLOB} gefunden - nichts zu pruefen.")
        return 0

    all_errors: list[str] = []
    for path in files:
        all_errors.extend(validate_file(path))

    if all_errors:
        print("Ausnahmeprozess-Pruefung fehlgeschlagen:")
        for err in all_errors:
            print(f"  - {err}")
        return 1

    print(f"Alle {len(files)} Ausnahmedatei(en) strukturell konsistent.")
    print("Hinweis: Freigabepruefung erfolgt separat, siehe check-exception-approvals.py.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
