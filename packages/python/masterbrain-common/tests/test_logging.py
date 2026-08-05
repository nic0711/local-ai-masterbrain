import json
import logging

from masterbrain_common.logging import (
    configure_json_logging,
    get_correlation_id,
    new_correlation_id,
    set_correlation_id,
)


def test_correlation_id_default_is_dash():
    assert get_correlation_id() == "-"


def test_set_and_get_correlation_id():
    set_correlation_id("abc123")
    try:
        assert get_correlation_id() == "abc123"
    finally:
        set_correlation_id("-")


def test_new_correlation_id_is_unique():
    a = new_correlation_id()
    b = new_correlation_id()
    assert a != b
    assert len(a) == 32  # uuid4 hex


def test_configure_json_logging_emits_valid_json(capsys):
    configure_json_logging("test-service")
    set_correlation_id("corr-xyz")
    try:
        logging.getLogger("test").info("hello world")
    finally:
        set_correlation_id("-")

    captured = capsys.readouterr()
    lines = [line for line in captured.err.splitlines() if line.strip()]
    assert lines, "expected at least one log line on stderr"
    record = json.loads(lines[-1])
    assert record["message"] == "hello world"
    assert record["correlation_id"] == "corr-xyz"
    assert record["level"] == "INFO"
