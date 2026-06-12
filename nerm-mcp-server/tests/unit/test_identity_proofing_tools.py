from nerm.errors import NermApiError
from nerm.tools.identity_proofing import nerm_list_identity_proofing_results


def test_list_identity_proofing_results_happy_path(monkeypatch) -> None:
    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        return {"identity_proofing_results": [{"id": "ipr-1"}]}

    monkeypatch.setattr("nerm.tools.identity_proofing.NermHttpClient.request", fake_request)
    result = nerm_list_identity_proofing_results(
        limit=10,
        offset=0,
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert "error" not in result
    assert result["items"] == [{"id": "ipr-1"}]


def test_list_identity_proofing_results_maps_errors(monkeypatch) -> None:
    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        raise NermApiError(status=500, body="boom")

    monkeypatch.setattr("nerm.tools.identity_proofing.NermHttpClient.request", fake_request)
    result = nerm_list_identity_proofing_results(
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert result == {"error": "nerm_api_error", "status": 500, "body": "boom"}


def test_identity_proofing_normalizes_id_to_string(monkeypatch) -> None:
    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        return {"items": [{"id": 42}]}

    monkeypatch.setattr("nerm.tools.identity_proofing.NermHttpClient.request", fake_request)
    result = nerm_list_identity_proofing_results(
        limit=10,
        offset=0,
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert result["items"][0]["id"] == "42"


def test_identity_proofing_rejects_invalid_pagination_type() -> None:
    result = nerm_list_identity_proofing_results(
        limit="invalid",  # type: ignore[arg-type]
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert result["error"] == "invalid_pagination_spec"
