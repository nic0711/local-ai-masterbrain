"""Tests fuer scripts/ci/check-trivy-findings.py (Security Gate v2.1).

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

Plus upstream_blocked (v2.1, docs/planning/security/upstream-blocked.yml):
  normales fixed Finding -> blockiert
  fixed + gueltiger upstream_blocked-Eintrag -> nicht blockierend
  falsche Komponente -> blockiert
  falsches CVE -> blockiert
  abgelaufener Eintrag -> blockiert
  fehlende direct_package-Zuordnung (unbekannter Target) -> blockiert
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

# Bekannter Target-Pfad aus _TARGET_TO_DIRECT_PACKAGE im Skript, der auf
# direct_package "docker-ce-cli" abgebildet wird - fuer die upstream_blocked-
# Tests. Ein beliebiger anderer Pfad (z.B. "test-target") bleibt bewusst ohne
# direct_package-Zuordnung (leerer String), s. test_missing_direct_package_mapping_blocks.
KNOWN_TARGET = "usr/bin/docker"
KNOWN_DIRECT_PACKAGE = "docker-ce-cli"


def _report(vulns: list[dict], target: str = "test-target") -> dict:
    return {"Results": [{"Target": target, "Class": "os-pkgs", "Vulnerabilities": vulns}]}


def _vuln(cve: str, severity: str = "HIGH", pkg: str = "testpkg", fixed_version: str = "", status: str = "") -> dict:
    return {
        "VulnerabilityID": cve,
        "Severity": severity,
        "PkgName": pkg,
        "InstalledVersion": "1.0.0",
        "FixedVersion": fixed_version,
        "Status": status,
    }


def _write_upstream_blocked(
    path: Path,
    component: str = "test-component",
    cve: str = "CVE-2026-9000",
    direct_package: str = KNOWN_DIRECT_PACKAGE,
    recheck_after: str = "2099-01-01",
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "entries:\n"
        f'  - component: "{component}"\n'
        f'    cve: "{cve}"\n'
        f'    direct_package: "{direct_package}"\n'
        '    installed_package_version: "1.2.3"\n'
        '    upstream_component: "stdlib"\n'
        '    vulnerable_version: "v1.0.0"\n'
        '    fixed_version: "1.0.1"\n'
        '    package_source: "https://example.invalid/repo"\n'
        '    verified_on: "2026-08-24"\n'
        '    evidence: "test fixture"\n'
        f'    recheck_after: "{recheck_after}"\n',
        encoding="utf-8",
    )


class CheckTrivyFindingsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo_root = Path(self._tmp.name)
        (self.repo_root / "docs" / "planning" / "security-exceptions").mkdir(parents=True)

    def _run(
        self,
        vulns: list[dict],
        approved_exceptions_file: str | None = None,
        component: str = "test-component",
        target: str = "test-target",
    ):
        report_path = self.repo_root / "report.json"
        report_path.write_text(json.dumps(_report(vulns, target=target)), encoding="utf-8")
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

    # --- upstream_blocked (Security Gate v2.1) ---

    def test_normal_fixed_finding_without_upstream_blocked_entry_still_blocks(self):
        result = self._run(
            [_vuln("CVE-2026-1000", status="fixed", fixed_version="1.2.3")],
            target=KNOWN_TARGET,
        )
        self.assertEqual(result.returncode, 1, result.stdout)

    def test_valid_upstream_blocked_entry_suppresses_finding(self):
        _write_upstream_blocked(
            self.repo_root / "docs" / "planning" / "security" / "upstream-blocked.yml",
            component="test-component",
            cve="CVE-2026-1001",
        )
        result = self._run(
            [_vuln("CVE-2026-1001", status="fixed", fixed_version="1.2.3")],
            target=KNOWN_TARGET,
        )
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("UPSTREAM BLOCKED", result.stdout)

    def test_wrong_component_still_blocks(self):
        _write_upstream_blocked(
            self.repo_root / "docs" / "planning" / "security" / "upstream-blocked.yml",
            component="other-component",
            cve="CVE-2026-1002",
        )
        result = self._run(
            [_vuln("CVE-2026-1002", status="fixed", fixed_version="1.2.3")],
            target=KNOWN_TARGET,
            component="test-component",
        )
        self.assertEqual(result.returncode, 1, result.stdout)

    def test_wrong_cve_still_blocks(self):
        _write_upstream_blocked(
            self.repo_root / "docs" / "planning" / "security" / "upstream-blocked.yml",
            component="test-component",
            cve="CVE-2026-9999",
        )
        result = self._run(
            [_vuln("CVE-2026-1003", status="fixed", fixed_version="1.2.3")],
            target=KNOWN_TARGET,
        )
        self.assertEqual(result.returncode, 1, result.stdout)

    def test_expired_recheck_after_still_blocks(self):
        _write_upstream_blocked(
            self.repo_root / "docs" / "planning" / "security" / "upstream-blocked.yml",
            component="test-component",
            cve="CVE-2026-1004",
            recheck_after="2000-01-01",
        )
        result = self._run(
            [_vuln("CVE-2026-1004", status="fixed", fixed_version="1.2.3")],
            target=KNOWN_TARGET,
        )
        self.assertEqual(result.returncode, 1, result.stdout)

    def test_missing_direct_package_mapping_blocks(self):
        # target="test-target" ist keinem direct_package zugeordnet - selbst
        # ein sonst passender Eintrag (direct_package="") darf nicht matchen,
        # da find_upstream_blocked_entry() bei leerem direct_package sofort
        # None liefert (fail-closed).
        _write_upstream_blocked(
            self.repo_root / "docs" / "planning" / "security" / "upstream-blocked.yml",
            component="test-component",
            cve="CVE-2026-1005",
            direct_package="",
        )
        result = self._run(
            [_vuln("CVE-2026-1005", status="fixed", fixed_version="1.2.3")],
            target="test-target",
        )
        self.assertEqual(result.returncode, 1, result.stdout)

    def test_existing_security_exceptions_still_work_alongside_upstream_blocked(self):
        _write_upstream_blocked(
            self.repo_root / "docs" / "planning" / "security" / "upstream-blocked.yml",
            component="test-component",
            cve="CVE-2026-1006",
        )
        exc_path = self.repo_root / "docs" / "planning" / "security-exceptions" / "test-exc.yml"
        exc_path.write_text(
            "id: \"test-exception\"\n"
            "component: \"test-component\"\n"
            "severity: \"high\"\n"
            "cve: \"CVE-2026-1007\"\n"
            "expires_on: \"2099-01-01\"\n",
            encoding="utf-8",
        )
        approved_path = self.repo_root / "approved-exceptions.json"
        approved_path.write_text(json.dumps(["test-exception"]), encoding="utf-8")

        result = self._run(
            [_vuln("CVE-2026-1007", status="fixed", fixed_version="1.2.3")],
            approved_exceptions_file=str(approved_path),
        )
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("AUSGENOMMEN", result.stdout)


if __name__ == "__main__":
    unittest.main()
