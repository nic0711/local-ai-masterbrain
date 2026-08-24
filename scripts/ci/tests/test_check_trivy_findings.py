"""Tests fuer scripts/ci/check-trivy-findings.py (Security Gate v2).

Ruft das Skript als Subprozess auf (kein Import noetig - Dateiname enthaelt
Bindestriche) gegen synthetische Trivy-JSON-Reports und prueft Exit-Code +
Ausgabe. Deckt die vom Nutzer vorgegebene Kategorisierung ab:

  fixed + FixedVersion       -> blockiert
  fixed ohne FixedVersion    -> blockiert
  affected ohne FixedVersion -> nicht blockiert
  fix_deferred               -> nicht blockiert
  will_not_fix               -> nicht blockiert
  end_of_life                -> nicht blockiert, aber separat gezaehlt
  unknown + FixedVersion     -> blockiert
  unknown ohne FixedVersion  -> nicht blockiert
  gueltige Exception fuer actionable Finding -> nicht blockiert
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "check-trivy-findings.py"


def _report(vulns: list[dict]) -> dict:
    return {"Results": [{"Target": "test-target", "Class": "os-pkgs", "Vulnerabilities": vulns}]}


def _vuln(cve: str, severity: str = "HIGH", pkg: str = "testpkg", fixed_version: str = "", status: str = "") -> dict:
    return {
        "VulnerabilityID": cve,
        "Severity": severity,
        "PkgName": pkg,
        "InstalledVersion": "1.0.0",
        "FixedVersion": fixed_version,
        "Status": status,
    }


class CheckTrivyFindingsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo_root = Path(self._tmp.name)
        (self.repo_root / "docs" / "planning" / "security-exceptions").mkdir(parents=True)

    def _run(self, vulns: list[dict], approved_exceptions_file: str | None = None, component: str = "test-component"):
        report_path = self.repo_root / "report.json"
        report_path.write_text(json.dumps(_report(vulns)), encoding="utf-8")
        cmd = [
            sys.executable,
            str(SCRIPT),
            "--report",
            str(report_path),
            "--component",
            component,
        ]
        if approved_exceptions_file:
            cmd += ["--approved-exceptions-file", approved_exceptions_file]
        return subprocess.run(cmd, cwd=self.repo_root, capture_output=True, text=True)

    def test_fixed_status_with_fixed_version_blocks(self):
        result = self._run([_vuln("CVE-2026-0001", status="fixed", fixed_version="1.2.3")])
        self.assertEqual(result.returncode, 1, result.stdout)

    def test_fixed_status_without_fixed_version_blocks(self):
        result = self._run([_vuln("CVE-2026-0002", status="fixed", fixed_version="")])
        self.assertEqual(result.returncode, 1, result.stdout)

    def test_affected_without_fixed_version_does_not_block(self):
        result = self._run([_vuln("CVE-2026-0003", status="affected", fixed_version="")])
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("no_fix_available", result.stdout)

    def test_fix_deferred_does_not_block(self):
        result = self._run([_vuln("CVE-2026-0004", status="fix_deferred", fixed_version="")])
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("fix_deferred", result.stdout)

    def test_will_not_fix_does_not_block(self):
        result = self._run([_vuln("CVE-2026-0005", status="will_not_fix", fixed_version="")])
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("will_not_fix", result.stdout)

    def test_end_of_life_does_not_block_but_is_counted_separately(self):
        result = self._run([_vuln("CVE-2026-0006", status="end_of_life", fixed_version="")])
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("end_of_life", result.stdout)

    def test_unknown_status_with_fixed_version_blocks(self):
        result = self._run([_vuln("CVE-2026-0007", status="", fixed_version="2.0.0")])
        self.assertEqual(result.returncode, 1, result.stdout)

    def test_unknown_status_without_fixed_version_does_not_block(self):
        result = self._run([_vuln("CVE-2026-0008", status="", fixed_version="")])
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("unknown", result.stdout)

    def test_low_severity_never_blocks_regardless_of_status(self):
        result = self._run([_vuln("CVE-2026-0009", severity="LOW", status="fixed", fixed_version="1.0.1")])
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_approved_exception_suppresses_actionable_finding(self):
        exc_path = self.repo_root / "docs" / "planning" / "security-exceptions" / "test-exc.yml"
        exc_path.write_text(
            "id: \"test-exception\"\n"
            "component: \"test-component\"\n"
            "severity: \"high\"\n"
            "cve: \"CVE-2026-0010\"\n"
            "expires_on: \"2099-01-01\"\n",
            encoding="utf-8",
        )
        approved_path = self.repo_root / "approved-exceptions.json"
        approved_path.write_text(json.dumps(["test-exception"]), encoding="utf-8")

        result = self._run(
            [_vuln("CVE-2026-0010", status="fixed", fixed_version="1.2.3")],
            approved_exceptions_file=str(approved_path),
        )
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("AUSGENOMMEN", result.stdout)

    def test_unapproved_exception_does_not_suppress_finding(self):
        exc_path = self.repo_root / "docs" / "planning" / "security-exceptions" / "test-exc.yml"
        exc_path.write_text(
            "id: \"test-exception\"\n"
            "component: \"test-component\"\n"
            "severity: \"high\"\n"
            "cve: \"CVE-2026-0011\"\n"
            "expires_on: \"2099-01-01\"\n",
            encoding="utf-8",
        )
        # Keine --approved-exceptions-file uebergeben -> fail-closed.
        result = self._run([_vuln("CVE-2026-0011", status="fixed", fixed_version="1.2.3")])
        self.assertEqual(result.returncode, 1, result.stdout)

    def test_mixed_report_blocks_only_on_actionable_finding(self):
        vulns = [
            _vuln("CVE-2026-0020", status="affected", fixed_version=""),
            _vuln("CVE-2026-0021", status="will_not_fix", fixed_version=""),
            _vuln("CVE-2026-0022", status="fixed", fixed_version="9.9.9"),
        ]
        result = self._run(vulns)
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("1 actionable(s)", result.stdout)


if __name__ == "__main__":
    unittest.main()
