from nerm.errors import NermApiError
from nerm.tools import _reference_catalog
from nerm.tools.attributes import nerm_get_attribute, nerm_list_attributes
from nerm.tools.profile_types import nerm_get_profile_type, nerm_list_profile_types


def _reset_reference_cache() -> None:
    _reference_catalog._reference_cache = None


def test_profile_types_list_uses_cache(monkeypatch) -> None:
    _reset_reference_cache()
    calls = {"count": 0}

    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        calls["count"] += 1
        return {"items": [{"id": "pt-1"}, {"id": "pt-2"}]}

    monkeypatch.setattr("nerm.tools._reference_catalog.NermHttpClient.request", fake_request)

    first = nerm_list_profile_types(
        limit=1,
        offset=0,
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    second = nerm_list_profile_types(
        limit=1,
        offset=1,
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )

    assert first["items"] == [{"id": "pt-1"}]
    assert second["items"] == [{"id": "pt-2"}]
    assert calls["count"] == 1


def test_attributes_get_by_id(monkeypatch) -> None:
    _reset_reference_cache()

    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        return {"items": [{"id": "attr-1"}, {"id": "attr-2"}]}

    monkeypatch.setattr("nerm.tools._reference_catalog.NermHttpClient.request", fake_request)

    result = nerm_get_attribute(
        "attr-2",
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert result["id"] == "attr-2"


def test_profile_types_maps_api_error(monkeypatch) -> None:
    _reset_reference_cache()

    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        raise NermApiError(status=429, body="rate limited")

    monkeypatch.setattr("nerm.tools._reference_catalog.NermHttpClient.request", fake_request)

    result = nerm_get_profile_type(
        "pt-1",
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert result == {"error": "nerm_api_error", "status": 429, "body": "rate limited"}


def test_attributes_list_missing_credentials_returns_error(monkeypatch) -> None:
    _reset_reference_cache()
    monkeypatch.setattr(
        "nerm.tools._reference_catalog.resolve_connection",
        lambda **_: (_ for _ in ()).throw(ValueError("NERM base URL and bearer token are required.")),
    )
    result = nerm_list_attributes(limit=1, offset=0)
    assert result["error"] == "nerm_api_error"
    assert result["status"] == 400


def test_profile_types_list_rejects_invalid_pagination_type() -> None:
    result = nerm_list_profile_types(
        limit="invalid",  # type: ignore[arg-type]
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert result["error"] == "invalid_pagination_spec"


def test_get_attribute_normalizes_id_to_string(monkeypatch) -> None:
    _reset_reference_cache()

    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        return {"items": [{"id": 200}]}

    monkeypatch.setattr("nerm.tools._reference_catalog.NermHttpClient.request", fake_request)

    result = nerm_get_attribute(
        "200",
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert result["id"] == "200"


def test_attributes_list_treats_no_attributes_found_as_empty_catalog(monkeypatch) -> None:
    _reset_reference_cache()
    calls = {"n": 0}

    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        del self, method, path, timeout, json
        calls["n"] += 1
        if calls["n"] == 1:
            raise NermApiError(status=400, body='{"error":"no attributes found"}')
        raise AssertionError(f"unexpected additional call with params={params}")

    monkeypatch.setattr("nerm.tools._reference_catalog.NermHttpClient.request", fake_request)
    result = nerm_list_attributes(
        limit=10,
        offset=0,
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert "error" not in result
    assert result["items"] == []
    assert result["total"] == 0
