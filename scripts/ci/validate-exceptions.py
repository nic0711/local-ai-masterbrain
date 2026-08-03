#!/usr/bin/env python3
"""Struktur-, Ablauf- und Konsistenzpruefung fuer Security-Ausnahmedateien.

Prueft NUR Struktur, Ablaufdatum, Scope und Konsistenz einer Ausnahme unter
docs/planning/security-exceptions/*.yml. Eine hier vorhandene approvals-Liste
wird NICHT als tatsaechliche Freigabe gewertet - verbindliche Freigaben
entstehen ausschliesslich ueber echte GitHub-PR-Reviews auf die jeweilige
Datei, durchgesetzt durch Branch-Schutzregeln und CODEOWNERS. Dieses Skript
ersetzt keinen Freigabeprozess.
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

MIN_APPROVAL_COUNT = {"critical": 2, "high": 1}

EXCEPTIONS_GLOB = "docs/planning/security-exceptions/*.yml"


def validate_file(path: str) -> list[str]:
    errors: list[str] = []
    with open(path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    for field in REQUIRED_FIELDS:
        if not data.get(field):
            errors.append(f"{path}: Pflichtfeld '{field}' fehlt oder ist leer")

    severity = str(data.get("severity", "")).lower()
    if severity not in MIN_APPROVAL_COUNT:
        errors.append(
            f"{path}: severity '{data.get('severity')}' ungueltig, erwartet 'critical' oder 'high'"
        )
    else:
        approvals = data.get("approvals") or []
        if len(approvals) < MIN_APPROVAL_COUNT[severity]:
            errors.append(
                f"{path}: nur {len(approvals)} Eintraege in approvals, "
                f"strukturell mind. {MIN_APPROVAL_COUNT[severity]} fuer severity={severity} erwartet "
                "(strukturelle Zaehlung, ersetzt keine echte GitHub-Freigabe)"
            )

    requested_by = data.get("requested_by")
    approvals = data.get("approvals") or []
    if requested_by and requested_by in approvals:
        errors.append(
            f"{path}: requested_by ('{requested_by}') taucht in approvals auf - "
            "Antragsteller darf nicht sich selbst freigeben"
        )

    if not data.get("github_approval_ref"):
        errors.append(
            f"{path}: 'github_approval_ref' fehlt - ohne Verweis auf einen echten "
            "GitHub-PR-Review gilt diese Ausnahme nicht als freigegeben"
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
