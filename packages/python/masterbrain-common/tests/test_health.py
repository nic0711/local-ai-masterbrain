from masterbrain_common.health import ReadyCheck, health_response, ready_response, version_response


def test_health_response_is_always_ok():
    body, status = health_response()
    assert status == 200
    assert body == {"status": "ok"}


def test_ready_response_all_checks_pass():
    checks = [ReadyCheck("db", lambda: True), ReadyCheck("cache", lambda: True)]
    body, status = ready_response(checks)
    assert status == 200
    assert body["status"] == "ready"
    assert body["checks"] == {"db": "ok", "cache": "ok"}


def test_ready_response_one_check_fails():
    checks = [ReadyCheck("db", lambda: True), ReadyCheck("cache", lambda: False)]
    body, status = ready_response(checks)
    assert status == 503
    assert body["status"] == "not_ready"
    assert body["checks"] == {"db": "ok", "cache": "down"}


def test_ready_response_check_raising_exception_counts_as_down():
    def boom():
        raise RuntimeError("connection refused")

    checks = [ReadyCheck("db", boom)]
    body, status = ready_response(checks)
    assert status == 503
    assert body["checks"]["db"] == "down"


def test_ready_response_no_checks_is_ready():
    body, status = ready_response([])
    assert status == 200
    assert body["status"] == "ready"


def test_version_response_contains_no_secrets():
    body, status = version_response("auth-gateway", "1.0.0", "0.1.0", "abc1234")
    assert status == 200
    assert body == {
        "service": "auth-gateway",
        "service_version": "1.0.0",
        "masterbrain_common_version": "0.1.0",
        "git_commit": "abc1234",
    }
