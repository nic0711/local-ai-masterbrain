#!/usr/bin/env python3
"""Bewertet einen Trivy-JSON-Report gegen strukturierte Security-Ausnahmen.

Security Gate v2: Ein Critical/High-Finding blockiert (Exit 1) nur noch, wenn
es tatsaechlich behebbar ist ("actionable" - FixedVersion nicht leer ODER
Status == "fixed") UND keine passende, freigegebene Ausnahme existiert.
Findings ohne jede Handlungsoption (Status affected/fix_deferred/
will_not_fix/end_of_life/unknown ohne FixedVersion - typischerweise Debian-
Stable-Pakete, fuer die es upstream schlicht noch keinen Patch gibt) sind
durch keinen Rebuild und keine Code-Aenderung zu beheben und wuerden das Gate
sonst dauerhaft und ohne jede Handlungsoption rot halten. Sie werden
weiterhin VOLLSTAENDIG angezeigt und in der Zusammenfassung gezaehlt, aber
nicht mehr blockierend gewertet.

Der Exception-Mechanismus bleibt fuer actionable Findings unveraendert: eine
passende, nicht abgelaufene Ausnahme unter docs/planning/security-exceptions/
*.yml, deren `id` in der von scripts/ci/check-exception-approvals.py
erzeugten approved-exceptions.json (via --approved-exceptions-file) auftaucht
- d.h. zur Laufzeit echte, unabhaengige GitHub-PR-Reviews auf den aktuellen
head_sha erhalten hat - haelt ein sonst blockierendes Finding weiterhin vom
Exit 1 ab. Ohne uebergebene Freigabedatei gilt KEINE Ausnahme als freigegeben
(fail-closed), nicht "alles erlaubt".

Schreibt zusaetzlich eine erweiterte Zusammenfassung (Critical/High/
Actionable/Kategorien ohne Fix + Link zum vollstaendigen Report-Artefakt)
nach $GITHUB_STEP_SUMMARY, falls gesetzt - der volle Report wird nicht mehr
per SARIF nach GitHub Code Scanning hochgeladen (siehe ci.yml), sondern nur
noch als Workflow-Artefakt bereitgestellt.
"""
from __future__ import annotations

import argparse
import datetime
import glob
import json
import os
import sys

try:
    import yaml
except ImportError:
    print("FEHLER: PyYAML ist nicht installiert (pip install pyyaml).", file=sys.stderr)
    sys.exit(2)

BLOCKING_SEVERITIES = {"CRITICAL", "HIGH"}
EXCEPTIONS_GLOB = "docs/planning/security-exceptions/*.yml"

# Trivy-Status-Werte ohne existierenden Fix, gemappt auf die Kategorienamen
# der Zusammenfassung - unabhaengig davon bleibt "actionable" primaer an
# FixedVersion/"fixed" festgemacht, s. classify_finding().
_STATUS_TO_CATEGORY = {
    "affected": "no_fix_available",
    "fix_deferred": "fix_deferred",
    "will_not_fix": "will_not_fix",
    "end_of_life": "end_of_life",
}


def classify_finding(status: str, fixed_version: str) -> str:
    """Ordnet ein Finding einer der folgenden Kategorien zu:

    - "actionable": FixedVersion vorhanden ODER Status == "fixed" - ein
      Rebuild/Upgrade koennte das Finding tatsaechlich beheben.
    - "no_fix_available": Status == "affected", kein Fix bekannt.
    - "fix_deferred": Upstream hat den Fix bewusst verschoben.
    - "will_not_fix": Upstream wird nicht patchen (z.B. abgekuendigte Distro-Version).
    - "end_of_life": das Paket selbst ist EOL - typischerweise Migrations-/
      Plattformthema, kein Patch-Thema.
    - "unknown": kein erkannter Status und keine FixedVersion.
    """
    if fixed_version or status == "fixed":
        return "actionable"
    return _STATUS_TO_CATEGORY.get(status, "unknown")


def load_active_exceptions(approved_ids: set[str]) -> list[dict]:
    """Laedt Ausnahmen, die (a) nicht abgelaufen sind UND (b) deren `id` in
    approved_ids steht (echte, zur Laufzeit geprueft GitHub-Freigabe)."""
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
        exc_id = data.get("id", path)
        if exc_id not in approved_ids:
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


def write_step_summary(
    component: str,
    all_findings: list[dict],
    artifact_name: str | None,
    artifact_url: str | None,
) -> None:
    """Schreibt eine kompakte Markdown-Zusammenfassung nach
    $GITHUB_STEP_SUMMARY, falls die Variable gesetzt ist (nur innerhalb
    eines GitHub-Actions-Laufs der Fall). Lokal/ausserhalb von CI: no-op,
    kein Fehler - verhindert nicht das normale Skriptverhalten."""
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return

    critical = sum(1 for f in all_findings if f["severity"] == "CRITICAL")
    high = sum(1 for f in all_findings if f["severity"] == "HIGH")
    actionable = sum(1 for f in all_findings if f["category"] == "actionable")
    no_fix_available = sum(1 for f in all_findings if f["category"] == "no_fix_available")
    fix_deferred = sum(1 for f in all_findings if f["category"] == "fix_deferred")
    will_not_fix = sum(1 for f in all_findings if f["category"] == "will_not_fix")
    end_of_life = sum(1 for f in all_findings if f["category"] == "end_of_life")
    unknown = sum(1 for f in all_findings if f["category"] == "unknown")

    lines = [
        f"### Trivy Image-Scan: `{component}`",
        "",
        "| Metrik | Anzahl |",
        "|---|---|",
        f"| Critical | {critical} |",
        f"| High | {high} |",
        f"| Actionable (Fix verfuegbar) | {actionable} |",
        f"| No fix available | {no_fix_available} |",
        f"| Fix deferred | {fix_deferred} |",
        f"| Will not fix | {will_not_fix} |",
        f"| End of life | {end_of_life} |",
        f"| Unknown | {unknown} |",
        "",
    ]
    if end_of_life:
        lines.append(
            f"**{end_of_life} End-of-Life-Finding(s):** kein Patch-Thema, sondern "
            "Migration/Plattformwechsel pruefen (Paket selbst wird nicht mehr gepflegt)."
        )
        lines.append("")
    if artifact_name:
        if artifact_url:
            lines.append(f"Vollstaendiger Report (JSON + SARIF): [{artifact_name}]({artifact_url})")
        else:
            lines.append(f"Vollstaendiger Report (JSON + SARIF): Artefakt `{artifact_name}`")
        lines.append("")

    with open(summary_path, "a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True, help="Pfad zu trivy --format json Output")
    parser.add_argument("--component", required=True, help="Name der Komponente, z.B. 'ocr-service' oder 'repo-fs'")
    parser.add_argument("--image-digest", default=None, help="Image-Digest, falls Image-Scan")
    parser.add_argument(
        "--approved-exceptions-file",
        default=None,
        help="JSON-Liste freigegebener Ausnahme-IDs aus check-exception-approvals.py. "
        "Ohne diese Datei gilt fail-closed: keine Ausnahme wird angewendet.",
    )
    parser.add_argument(
        "--artifact-name",
        default=None,
        help="Name des Workflow-Artefakts mit dem vollstaendigen JSON/SARIF-Report, "
        "fuer die GitHub-Step-Summary.",
    )
    parser.add_argument(
        "--artifact-url",
        default=None,
        help="URL des Workflow-Artefakts (z.B. steps.<id>.outputs.artifact-url), "
        "fuer die GitHub-Step-Summary. Optional.",
    )
    args = parser.parse_args()

    with open(args.report, encoding="utf-8") as fh:
        report = json.load(fh)

    approved_ids: set[str] = set()
    if args.approved_exceptions_file:
        try:
            with open(args.approved_exceptions_file, encoding="utf-8") as fh:
                approved_ids = set(json.load(fh))
        except FileNotFoundError:
            print(
                f"Hinweis: {args.approved_exceptions_file} nicht gefunden - "
                "keine Ausnahme wird als freigegeben behandelt (fail-closed)."
            )
    else:
        print("Hinweis: keine --approved-exceptions-file uebergeben - fail-closed, keine Ausnahmen aktiv.")

    active_exceptions = load_active_exceptions(approved_ids)

    all_findings = []
    blocking_findings = []

    for result in report.get("Results", []) or []:
        for vuln in result.get("Vulnerabilities", []) or []:
            severity = vuln.get("Severity", "UNKNOWN")
            cve = vuln.get("VulnerabilityID", "")
            pkg = vuln.get("PkgName", "")
            installed = vuln.get("InstalledVersion", "")
            fixed_version = vuln.get("FixedVersion", "")
            status = vuln.get("Status", "")
            category = classify_finding(status, fixed_version)
            actionable = category == "actionable"

            covered = False
            covering_id = None
            if severity in BLOCKING_SEVERITIES and actionable:
                for exc in active_exceptions:
                    if exception_covers(exc, cve, args.component, args.image_digest):
                        covered = True
                        covering_id = exc.get("id", exc.get("_source_file"))
                        break

            entry = {
                "cve": cve,
                "severity": severity,
                "package": pkg,
                "installed_version": installed,
                "fixed_version": fixed_version,
                "status": status,
                "category": category,
                "covered_by_exception": covering_id if covered else None,
            }
            all_findings.append(entry)

            if severity in BLOCKING_SEVERITIES and actionable and not covered:
                blocking_findings.append(entry)

    print(f"Komponente: {args.component}" + (f" (Image-Digest: {args.image_digest})" if args.image_digest else ""))
    print(f"Gesamtzahl Findings: {len(all_findings)} (alle Severities, vollstaendig sichtbar):")
    for f in all_findings:
        if f["covered_by_exception"]:
            note = f"AUSGENOMMEN ({f['covered_by_exception']})"
        elif f["category"] != "actionable":
            note = f"nicht blockierend ({f['category']})"
        else:
            note = "-"
        print(
            f"  - [{f['severity']}] {f['cve']} in {f['package']}@{f['installed_version']} "
            f"(status={f['status'] or 'unknown'}, fixed={f['fixed_version'] or '-'})  {note}"
        )

    write_step_summary(args.component, all_findings, args.artifact_name, args.artifact_url)

    if blocking_findings:
        print(
            f"\n{len(blocking_findings)} actionable(s) Critical/High-Finding(s) OHNE gueltige, "
            "freigegebene Ausnahme -> blockiert diesen Check."
        )
        return 1

    print("\nKeine blockierenden (actionable, nicht ausgenommenen) Critical/High-Findings.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
