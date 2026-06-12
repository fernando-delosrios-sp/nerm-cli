import httpx
import pytest

from nerm.client.http_client import NermHttpClient
from nerm.errors import NermApiError


def test_http_client_retries_request_errors_then_succeeds(monkeypatch) -> None:
    client = NermHttpClient(base_url="https://tenant.example.com", bearer_token="Bearer token")
    calls = {"n": 0}

    def fake_request(method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        calls["n"] += 1
        if calls["n"] < 3:
            request = httpx.Request(method, f"https://tenant.example.com{path}")
            raise httpx.ConnectError("boom", request=request)
        return httpx.Response(status_code=200, json={"items": []})

    monkeypatch.setattr(client._client, "request", fake_request)
    result = client.request("GET", "/profiles")
    assert result == {"items": []}
    assert calls["n"] == 3


def test_http_client_raises_structured_error_on_exhausted_request_errors(monkeypatch) -> None:
    client = NermHttpClient(base_url="https://tenant.example.com", bearer_token="Bearer token")

    def fake_request(method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        request = httpx.Request(method, f"https://tenant.example.com{path}")
        raise httpx.ReadTimeout("timed out", request=request)

    monkeypatch.setattr(client._client, "request", fake_request)
    with pytest.raises(NermApiError) as excinfo:
        client.request("GET", "/profiles")
    assert excinfo.value.status == 502
    assert "transport error:" in excinfo.value.body


def test_http_client_returns_empty_dict_for_empty_2xx_body(monkeypatch) -> None:
    client = NermHttpClient(base_url="https://tenant.example.com", bearer_token="Bearer token")

    def fake_request(method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        return httpx.Response(status_code=204, text="")

    monkeypatch.setattr(client._client, "request", fake_request)
    result = client.request("DELETE", "/delegations/1")
    assert result == {}


def test_http_client_raises_structured_error_on_invalid_json_2xx(monkeypatch) -> None:
    client = NermHttpClient(base_url="https://tenant.example.com", bearer_token="Bearer token")

    def fake_request(method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        return httpx.Response(status_code=200, text="not-json")

    monkeypatch.setattr(client._client, "request", fake_request)
    with pytest.raises(NermApiError) as excinfo:
        client.request("GET", "/profiles")
    assert excinfo.value.status == 502
    assert "invalid JSON response:" in excinfo.value.body


def test_http_client_retries_429_then_succeeds(monkeypatch) -> None:
    client = NermHttpClient(base_url="https://tenant.example.com", bearer_token="Bearer token")
    calls = {"n": 0}

    def fake_request(method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(status_code=429, text="rate limited")
        return httpx.Response(status_code=200, json={"items": [{"id": "ok"}]})

    monkeypatch.setattr(client._client, "request", fake_request)
    result = client.request("GET", "/profiles")
    assert result["items"] == [{"id": "ok"}]
    assert calls["n"] == 3


def test_http_client_fails_fast_on_401_without_retries(monkeypatch) -> None:
    client = NermHttpClient(base_url="https://tenant.example.com", bearer_token="Bearer token")
    calls = {"n": 0}

    def fake_request(method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        calls["n"] += 1
        return httpx.Response(status_code=401, text="unauthorized")

    monkeypatch.setattr(client._client, "request", fake_request)
    with pytest.raises(NermApiError) as excinfo:
        client.request("GET", "/profiles")
    assert excinfo.value.status == 401
    assert calls["n"] == 1


def test_http_client_wraps_list_json_into_items_dict(monkeypatch) -> None:
    client = NermHttpClient(base_url="https://tenant.example.com", bearer_token="Bearer token")

    def fake_request(method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        return httpx.Response(status_code=200, json=[{"id": "x"}])

    monkeypatch.setattr(client._client, "request", fake_request)
    result = client.request("GET", "/profiles")
    assert result == {"items": [{"id": "x"}]}
