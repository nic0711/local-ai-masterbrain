#!/usr/bin/env python3
"""Bewertet einen Trivy-JSON-Report gegen strukturierte Security-Ausnahmen.

Bestehende Critical/High-Findings werden IMMER vollstaendig ausgegeben
(sichtbar, keine pauschale Unterdrueckung). Ein Fund blockiert (Exit 1) nur
dann NICHT, wenn eine passende, nicht abgelaufene Ausnahme unter
docs/planning/security-exceptions/*.yml existiert, die zusaetzlich einen
nicht-leeren 'github_approval_ref' traegt (Verweis auf einen echten
GitHub-PR-Review). Eine reine approvals-Liste in der YAML-Datei zaehlt NICHT
als Freigabe.
"""
from __future__ import annotations

import argparse
import datetime
import glob
import json
import sys

try:
    import yaml
except ImportError:
    print("FEHLER: PyYAML ist nicht installiert (pip install pyyaml).", file=sys.stderr)
    sys.exit(2)

BLOCKING_SEVERITIES = {"CRITICAL", "HIGH"}
EXCEPTIONS_GLOB = "docs/planning/security-exceptions/*.yml"


def load_active_exceptions() -> list[dict]:
    active = []
    today = datetime.date.today()
    for path in sorted(glob.glob(EXCEPTIONS_GLOB)):
        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        expires_on = data.get("expires_on")
        if not expires_on:
            continue
        try:
            expiry = datetime.date.fromisoformat(str(expires_on))
        except ValueError:
            continue
        if expiry < today:
            continue
        if not data.get("github_approval_ref"):
            continue
        data["_source_file"] = path
        active.append(data)
    return active


def exception_covers(exc: dict, cve: str, component: str, image_digest: str | None) -> bool:
    if exc.get("cve") != cve:
        return False
    if exc.get("component") != component:
        return False
    exc_digest = exc.get("affected_image_digest")
    if exc_digest and image_digest and exc_digest != image_digest:
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True, help="Pfad zu trivy --format json Output")
    parser.add_argument("--component", required=True, help="Name der Komponente, z.B. 'ocr-service' oder 'repo-fs'")
    parser.add_argument("--image-digest", default=None, help="Image-Digest, falls Image-Scan")
    args = parser.parse_args()

    with open(args.report, encoding="utf-8") as fh:
        report = json.load(fh)

    active_exceptions = load_active_exceptions()

    all_findings = []
    blocking_findings = []

    for result in report.get("Results", []) or []:
        for vuln in result.get("Vulnerabilities", []) or []:
            severity = vuln.get("Severity", "UNKNOWN")
            cve = vuln.get("VulnerabilityID", "")
            pkg = vuln.get("PkgName", "")
            installed = vuln.get("InstalledVersion", "")

            covered = False
            covering_ref = None
            if severity in BLOCKING_SEVERITIES:
                for exc in active_exceptions:
                    if exception_covers(exc, cve, args.component, args.image_digest):
                        covered = True
                        covering_ref = exc.get("github_approval_ref")
                        break

            entry = {
                "cve": cve,
                "severity": severity,
                "package": pkg,
                "installed_version": installed,
                "covered_by_exception": covering_ref if covered else None,
            }
            all_findings.append(entry)

            if severity in BLOCKING_SEVERITIES and not covered:
                blocking_findings.append(entry)

    print(f"Komponente: {args.component}" + (f" (Image-Digest: {args.image_digest})" if args.image_digest else ""))
    print(f"Gesamtzahl Findings: {len(all_findings)} (alle Severities, vollstaendig sichtbar):")
    for f in all_findings:
        status = f"AUSGENOMMEN ({f['covered_by_exception']})" if f["covered_by_exception"] else "-"
        print(f"  - [{f['severity']}] {f['cve']} in {f['package']}@{f['installed_version']}  {status}")

    if blocking_findings:
        print(
            f"\n{len(blocking_findings)} Critical/High-Finding(s) OHNE gueltige, freigegebene Ausnahme "
            "-> blockiert diesen Check."
        )
        return 1

    print("\nKeine blockierenden (nicht ausgenommenen) Critical/High-Findings.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
