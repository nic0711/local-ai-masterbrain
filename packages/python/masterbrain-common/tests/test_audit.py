import json
import logging

from masterbrain_common.audit import log_event


def test_log_event_emits_structured_record(caplog):
    with caplog.at_level(logging.INFO, logger="audit"):
        log_event(actor="user-1", action="start", target="grafana", result="ok")

    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.audit is True
    assert record.actor == "user-1"
    assert record.action == "start"
    assert record.target == "grafana"
    assert record.result == "ok"


def test_log_event_accepts_extra_fields(caplog):
    with caplog.at_level(logging.INFO, logger="audit"):
        log_event(
            actor="user-1",
            action="macro",
            target="backup-and-restart",
            result="partial",
            macro_id="nightly",
        )

    record = caplog.records[0]
    assert record.macro_id == "nightly"


def test_log_event_json_serializable_via_json_formatter(capsys):
    from pythonjsonlogger import json as jsonlogger

    handler = logging.StreamHandler()
    handler.setFormatter(jsonlogger.JsonFormatter())
    logger = logging.getLogger("audit")
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.INFO)

    log_event(actor="user-2", action="stop", target="n8n", result="ok")

    captured = capsys.readouterr()
    lines = [line for line in captured.err.splitlines() if line.strip()]
    record = json.loads(lines[-1])
    assert record["actor"] == "user-2"
    assert record["result"] == "ok"
