"""
Tests fuer clone_supabase_repo() in start_services.py.

Diese Funktion verifiziert ausschliesslich, dass 'supabase/' ein korrekt
initialisiertes Git-Submodule ist, und darf dabei NIEMALS eine mutierende
Git-Operation ausfuehren (kein pull/clone/checkout/submodule update/
sparse-checkout). Alle git-Aufrufe laufen ueber run_command(), die hier
gemockt und protokolliert wird - die Tests pruefen die tatsaechlich
ausgefuehrten Kommandos, nicht Quelltextstrings (z.B. den Reparaturhinweis).
"""
import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Tokens, die in KEINEM ausgefuehrten git-Kommando vorkommen duerfen.
_MUTATING_TOKENS = ("pull", "clone", "checkout", "sparse-checkout")


def _assert_no_mutating_git_calls(calls):
    """Prueft die Liste tatsaechlich ausgefuehrter Kommandos (nicht
    Quelltext/Fehlermeldungen) auf verbotene mutierende Operationen."""
    for cmd in calls:
        for token in _MUTATING_TOKENS:
            assert token not in cmd, f"verbotene Operation '{token}' in {cmd}"
        if "submodule" in cmd:
            idx = cmd.index("submodule")
            assert not (idx + 1 < len(cmd) and cmd[idx + 1] == "update"), (
                f"verbotenes 'git submodule update' in {cmd}"
            )


class _FakeResult:
    def __init__(self, returncode=0, stdout=""):
        self.returncode = returncode
        self.stdout = stdout


def _make_fake_run_command(responses, calls_log):
    """responses: dict[tuple(cmd) -> _FakeResult]. Nicht erfasste Kommandos
    fuehren zu einem AssertionError (explizit statt stillschweigendem
    Default), damit Tests keine unerwarteten echten Aufrufe verschleiern."""

    def fake_run_command(cmd, cwd=None, env=None, check=True, capture_output=False):
        cmd = list(cmd)
        calls_log.append(cmd)
        key = tuple(cmd)
        if key not in responses:
            raise AssertionError(f"unerwarteter run_command()-Aufruf: {cmd}")
        return responses[key]

    return fake_run_command


@pytest.fixture
def ss(monkeypatch, tmp_path):
    """Laedt start_services frisch, mit cwd auf ein leeres tmp_path gesetzt."""
    monkeypatch.chdir(tmp_path)
    if REPO_ROOT not in sys.path:
        sys.path.insert(0, REPO_ROOT)
    sys.modules.pop("start_services", None)
    import start_services as mod
    yield mod
    sys.modules.pop("start_services", None)


def _toplevel_cmd():
    return ("git", "-C", "supabase", "rev-parse", "--show-toplevel")


def _superproject_cmd():
    return ("git", "-C", "supabase", "rev-parse", "--show-superproject-working-tree")


def _expected_head_cmd():
    return ("git", "rev-parse", "HEAD:supabase")


def _actual_head_cmd():
    return ("git", "-C", "supabase", "rev-parse", "HEAD")


# ---------------------------------------------------------------------------
# 1. Korrektes Submodule: kein SystemExit, keine Mutation.
# ---------------------------------------------------------------------------
def test_correctly_initialized_submodule_passes(ss, monkeypatch, tmp_path):
    (tmp_path / "supabase" / "docker").mkdir(parents=True)
    calls = []
    responses = {
        _toplevel_cmd(): _FakeResult(0, str(tmp_path / "supabase") + "\n"),
        _superproject_cmd(): _FakeResult(0, str(tmp_path) + "\n"),
        _expected_head_cmd(): _FakeResult(0, "abc123\n"),
        _actual_head_cmd(): _FakeResult(0, "abc123\n"),
    }
    monkeypatch.setattr(ss, "run_command", _make_fake_run_command(responses, calls))

    ss.clone_supabase_repo()  # darf NICHT raisen

    _assert_no_mutating_git_calls(calls)
    assert len(calls) == 4


# ---------------------------------------------------------------------------
# 2. supabase/docker fehlt: sofortiger SystemExit, keinerlei Git-Mutation
#    (hier sogar: gar kein Git-Aufruf ueberhaupt).
# ---------------------------------------------------------------------------
def test_missing_supabase_docker_fails_closed_without_any_git_call(ss, monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(ss, "run_command", _make_fake_run_command({}, calls))

    with pytest.raises(SystemExit) as exc_info:
        ss.clone_supabase_repo()

    assert "supabase/docker" in str(exc_info.value)
    assert calls == []
    _assert_no_mutating_git_calls(calls)


# ---------------------------------------------------------------------------
# 3. supabase/ ohne eigenes Git-Metadatum: show-toplevel liefert das
#    Parent-Repo statt supabase/ (Kernszenario des urspruenglichen Vorfalls).
# ---------------------------------------------------------------------------
def test_supabase_without_own_git_reports_parent_toplevel(ss, monkeypatch, tmp_path):
    (tmp_path / "supabase" / "docker").mkdir(parents=True)
    calls = []
    responses = {
        # Ohne eigenes .git in supabase/ liefert git den PARENT-Toplevel.
        _toplevel_cmd(): _FakeResult(0, str(tmp_path) + "\n"),
    }
    monkeypatch.setattr(ss, "run_command", _make_fake_run_command(responses, calls))

    with pytest.raises(SystemExit) as exc_info:
        ss.clone_supabase_repo()

    assert "eigenstaendig" in str(exc_info.value)
    _assert_no_mutating_git_calls(calls)


# ---------------------------------------------------------------------------
# 4. Unabhaengiger Git-Clone unter supabase/: eigenes .git vorhanden
#    (show-toplevel korrekt), aber kein Superprojekt-Bezug.
# ---------------------------------------------------------------------------
def test_independent_clone_without_superproject_fails(ss, monkeypatch, tmp_path):
    (tmp_path / "supabase" / "docker").mkdir(parents=True)
    calls = []
    responses = {
        _toplevel_cmd(): _FakeResult(0, str(tmp_path / "supabase") + "\n"),
        # Eigenstaendiges Repo ohne Superprojekt: git liefert leeren Output.
        _superproject_cmd(): _FakeResult(0, ""),
    }
    monkeypatch.setattr(ss, "run_command", _make_fake_run_command(responses, calls))

    with pytest.raises(SystemExit) as exc_info:
        ss.clone_supabase_repo()

    assert "Submodule" in str(exc_info.value)
    _assert_no_mutating_git_calls(calls)


# ---------------------------------------------------------------------------
# 5. Falscher Superprojekt-Pfad (zeigt auf irgendein anderes Verzeichnis).
# ---------------------------------------------------------------------------
def test_wrong_superproject_path_fails(ss, monkeypatch, tmp_path):
    (tmp_path / "supabase" / "docker").mkdir(parents=True)
    other_dir = tmp_path / "irgendwo-anders"
    other_dir.mkdir()
    calls = []
    responses = {
        _toplevel_cmd(): _FakeResult(0, str(tmp_path / "supabase") + "\n"),
        _superproject_cmd(): _FakeResult(0, str(other_dir) + "\n"),
    }
    monkeypatch.setattr(ss, "run_command", _make_fake_run_command(responses, calls))

    with pytest.raises(SystemExit):
        ss.clone_supabase_repo()

    _assert_no_mutating_git_calls(calls)


# ---------------------------------------------------------------------------
# 6. Submodule-HEAD != Gitlink: SystemExit, beide SHAs in der Meldung.
# ---------------------------------------------------------------------------
def test_head_mismatch_fails_with_both_shas_in_message(ss, monkeypatch, tmp_path):
    (tmp_path / "supabase" / "docker").mkdir(parents=True)
    calls = []
    responses = {
        _toplevel_cmd(): _FakeResult(0, str(tmp_path / "supabase") + "\n"),
        _superproject_cmd(): _FakeResult(0, str(tmp_path) + "\n"),
        _expected_head_cmd(): _FakeResult(0, "expectedsha123\n"),
        _actual_head_cmd(): _FakeResult(0, "actualsha456\n"),
    }
    monkeypatch.setattr(ss, "run_command", _make_fake_run_command(responses, calls))

    with pytest.raises(SystemExit) as exc_info:
        ss.clone_supabase_repo()

    message = str(exc_info.value)
    assert "expectedsha123" in message
    assert "actualsha456" in message
    _assert_no_mutating_git_calls(calls)


# ---------------------------------------------------------------------------
# 7. rev-parse schlaegt fehl (non-zero Returncode oder leerer Output).
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("broken_cmd", [_expected_head_cmd(), _actual_head_cmd()])
def test_rev_parse_failure_fails_closed(ss, monkeypatch, tmp_path, broken_cmd):
    (tmp_path / "supabase" / "docker").mkdir(parents=True)
    calls = []
    responses = {
        _toplevel_cmd(): _FakeResult(0, str(tmp_path / "supabase") + "\n"),
        _superproject_cmd(): _FakeResult(0, str(tmp_path) + "\n"),
        _expected_head_cmd(): _FakeResult(0, "abc123\n"),
        _actual_head_cmd(): _FakeResult(0, "abc123\n"),
    }
    responses[broken_cmd] = _FakeResult(1, "")  # Fehlschlag ueberschreiben
    monkeypatch.setattr(ss, "run_command", _make_fake_run_command(responses, calls))

    with pytest.raises(SystemExit):
        ss.clone_supabase_repo()

    _assert_no_mutating_git_calls(calls)


# ---------------------------------------------------------------------------
# 8. Cross-Cutting Security-Test: in KEINEM der obigen Pfade darf jemals
#    eine mutierende Git-Operation ausgefuehrt worden sein. Prueft die
#    tatsaechlich protokollierten Kommandos, nicht den Quelltext/die
#    Fehlermeldungen (der String "git submodule update --init -- supabase"
#    darf dort als reiner Hinweistext vorkommen).
# ---------------------------------------------------------------------------
def test_repair_hint_string_is_not_an_executed_command(ss, monkeypatch, tmp_path):
    (tmp_path / "supabase" / "docker").mkdir(parents=True)
    calls = []
    responses = {
        _toplevel_cmd(): _FakeResult(0, str(tmp_path) + "\n"),  # Parent statt supabase/
    }
    monkeypatch.setattr(ss, "run_command", _make_fake_run_command(responses, calls))

    with pytest.raises(SystemExit) as exc_info:
        ss.clone_supabase_repo()

    # Der Reparaturhinweis DARF als Text in der Fehlermeldung stehen ...
    assert "git submodule update --init -- supabase" in str(exc_info.value)
    # ... aber es darf NIEMALS tatsaechlich als Kommando ausgefuehrt worden sein.
    for cmd in calls:
        assert cmd != ["git", "submodule", "update", "--init", "--", "supabase"]
    _assert_no_mutating_git_calls(calls)


# ---------------------------------------------------------------------------
# 6 (Aufgabenbeschreibung) / zentraler Regressionstest: der urspruengliche
# Vorfall - supabase/docker existiert, supabase/ hat kein eigenes Git-
# Metadatum, git -C supabase wuerde deshalb das Parent-Repo erkennen und
# potenziell `git pull` dort ausfuehren. clone_supabase_repo() muss VOR
# jeder mutierenden Operation abbrechen.
# ---------------------------------------------------------------------------
def test_regression_original_incident_aborts_before_any_mutating_operation(ss, monkeypatch, tmp_path):
    (tmp_path / "supabase" / "docker").mkdir(parents=True)
    calls = []
    responses = {
        # git -C supabase laeuft mangels eigenem .git im Parent-Repo und
        # meldet dessen Toplevel zurueck - exakt der urspruengliche Fehler.
        _toplevel_cmd(): _FakeResult(0, str(tmp_path) + "\n"),
    }
    monkeypatch.setattr(ss, "run_command", _make_fake_run_command(responses, calls))

    with pytest.raises(SystemExit):
        ss.clone_supabase_repo()

    # Kein "git pull" (oder irgendeine andere Mutation) wurde ausgefuehrt.
    assert not any("pull" in cmd for cmd in calls)
    _assert_no_mutating_git_calls(calls)
