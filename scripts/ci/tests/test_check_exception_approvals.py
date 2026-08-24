"""Tests fuer scripts/ci/check-exception-approvals.py, insbesondere die
Push-Kontext-Aufloesung (Phase 3a): main() muss auf einem push-Event (kein
PR_NUMBER) den zugehoerigen, bereits gemergten PR ueber commits/{sha}/pulls
finden und dessen Reviews auf dem letzten PR-Branch-Commit (nicht dem
Squash-Merge-Commit) pruefen.

Laedt das Skript per importlib (Dateiname enthaelt Bindestriche) und
mockt die netzwerkgebundenen fetch_*-Funktionen direkt auf dem Modul -
kein echter GitHub-API-Zugriff noetig.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "check-exception-approvals.py"

_spec = importlib.util.spec_from_file_location("check_exception_approvals", SCRIPT)
cea = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cea)  # type: ignore[union-attr]


def _write_exception(path: Path, exc_id: str, severity: str, cve: str = "") -> None:
    path.write_text(
        f'id: "{exc_id}"\n'
        f'component: "test-component"\n'
        f'severity: "{severity}"\n'
        f'cve: "{cve}"\n'
        'expires_on: "2099-01-01"\n',
        encoding="utf-8",
    )


class PushContextResolutionTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo_root = Path(self._tmp.name)
        (self.repo_root / "docs" / "planning" / "security-exceptions").mkdir(parents=True)
        self._old_cwd = Path.cwd()
        import os

        os.chdir(self.repo_root)
        self.addCleanup(os.chdir, self._old_cwd)

    def _run_main(self, argv: list[str]) -> int:
        with mock.patch.object(sys, "argv", ["check-exception-approvals.py", *argv]):
            return cea.main()

    def test_push_context_resolves_merged_pr_and_approves(self):
        _write_exception(
            self.repo_root / "docs" / "planning" / "security-exceptions" / "exc.yml",
            "exc-1",
            "high",
            "CVE-2026-0001",
        )
        pr = {
            "number": 42,
            "merged_at": "2026-08-24T00:00:00Z",
            "merge_commit_sha": "deadbeef",
            "head": {"sha": "cafef00d"},
            "user": {"login": "author"},
        }
        review = {
            "user": {"login": "reviewer"},
            "state": "APPROVED",
            "commit_id": "cafef00d",
            "submitted_at": "2026-08-23T00:00:00Z",
        }
        with mock.patch.object(cea, "fetch_prs_for_commit", return_value=[pr]), \
             mock.patch.object(cea, "fetch_reviews", return_value=[review]):
            rc = self._run_main(["--repo", "nic0711/local-ai-masterbrain", "--head-sha", "deadbeef", "--token", "t"])
        self.assertEqual(rc, 0)
        approved = json.loads((self.repo_root / "approved-exceptions.json").read_text())
        self.assertEqual(approved, ["exc-1"])

    def test_push_context_no_merged_pr_found_approves_nothing(self):
        _write_exception(
            self.repo_root / "docs" / "planning" / "security-exceptions" / "exc.yml",
            "exc-1",
            "high",
            "CVE-2026-0002",
        )
        with mock.patch.object(cea, "fetch_prs_for_commit", return_value=[]):
            rc = self._run_main(["--repo", "nic0711/local-ai-masterbrain", "--head-sha", "deadbeef", "--token", "t"])
        self.assertEqual(rc, 0)
        approved = json.loads((self.repo_root / "approved-exceptions.json").read_text())
        self.assertEqual(approved, [])

    def test_push_context_merge_commit_sha_mismatch_aborts_safely(self):
        _write_exception(
            self.repo_root / "docs" / "planning" / "security-exceptions" / "exc.yml",
            "exc-1",
            "high",
            "CVE-2026-0003",
        )
        pr = {
            "number": 42,
            "merged_at": "2026-08-24T00:00:00Z",
            "merge_commit_sha": "other-sha",
            "head": {"sha": "cafef00d"},
            "user": {"login": "author"},
        }
        review = {
            "user": {"login": "reviewer"},
            "state": "APPROVED",
            "commit_id": "cafef00d",
            "submitted_at": "2026-08-23T00:00:00Z",
        }
        with mock.patch.object(cea, "fetch_prs_for_commit", return_value=[pr]), \
             mock.patch.object(cea, "fetch_reviews", return_value=[review]):
            rc = self._run_main(["--repo", "nic0711/local-ai-masterbrain", "--head-sha", "deadbeef", "--token", "t"])
        self.assertEqual(rc, 0)
        approved = json.loads((self.repo_root / "approved-exceptions.json").read_text())
        self.assertEqual(approved, [])

    def test_push_context_multiple_merged_candidates_approves_nothing(self):
        _write_exception(
            self.repo_root / "docs" / "planning" / "security-exceptions" / "exc.yml",
            "exc-1",
            "high",
            "CVE-2026-0004",
        )
        pr_a = {"number": 1, "merged_at": "2026-08-24T00:00:00Z", "merge_commit_sha": "deadbeef", "head": {"sha": "a"}}
        pr_b = {"number": 2, "merged_at": "2026-08-24T00:00:00Z", "merge_commit_sha": "deadbeef", "head": {"sha": "b"}}
        with mock.patch.object(cea, "fetch_prs_for_commit", return_value=[pr_a, pr_b]):
            rc = self._run_main(["--repo", "nic0711/local-ai-masterbrain", "--head-sha", "deadbeef", "--token", "t"])
        self.assertEqual(rc, 0)
        approved = json.loads((self.repo_root / "approved-exceptions.json").read_text())
        self.assertEqual(approved, [])

    def test_direct_pr_context_unchanged(self):
        _write_exception(
            self.repo_root / "docs" / "planning" / "security-exceptions" / "exc.yml",
            "exc-1",
            "high",
            "CVE-2026-0005",
        )
        review = {
            "user": {"login": "reviewer"},
            "state": "APPROVED",
            "commit_id": "prheadsha",
            "submitted_at": "2026-08-23T00:00:00Z",
        }
        with mock.patch.object(cea, "fetch_pr", return_value={"user": {"login": "author"}}), \
             mock.patch.object(cea, "fetch_reviews", return_value=[review]):
            rc = self._run_main(
                [
                    "--repo",
                    "nic0711/local-ai-masterbrain",
                    "--pr-number",
                    "7",
                    "--head-sha",
                    "prheadsha",
                    "--token",
                    "t",
                ]
            )
        self.assertEqual(rc, 0)
        approved = json.loads((self.repo_root / "approved-exceptions.json").read_text())
        self.assertEqual(approved, ["exc-1"])


if __name__ == "__main__":
    unittest.main()
