from masterbrain_common.errors import error_response


def test_error_response_default_code():
    assert error_response("Unauthorized") == {"error": "Unauthorized", "code": "error"}


def test_error_response_custom_code():
    body = error_response("Dienst nicht erlaubt", code="not_allowed")
    assert body == {"error": "Dienst nicht erlaubt", "code": "not_allowed"}
