from nerm.errors import NermApiError
from nerm.tools._reference_catalog import execute_with_nerm_error_json


def test_nerm_error_shape() -> None:
    err = NermApiError(status=500, body="failed")
    assert err.as_error_json() == {"error": "nerm_api_error", "status": 500, "body": "failed"}


def test_execute_with_nerm_error_json_maps_unexpected_exception() -> None:
    result = execute_with_nerm_error_json(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    assert result["error"] == "nerm_api_error"
    assert result["status"] == 500
    assert "unexpected error: boom" in result["body"]
