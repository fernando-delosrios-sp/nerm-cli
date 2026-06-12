import httpx
import logging

from nerm.client.http_client import NermHttpClient
from nerm.config import get_settings


def test_http_client_logs_request_response_without_body_by_default(monkeypatch, caplog) -> None:
    monkeypatch.setenv("NERM_DEBUG_LOG_BODIES", "0")
    get_settings.cache_clear()
    client = NermHttpClient(base_url="https://tenant.example.com", bearer_token="Bearer token")

    def fake_request(method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        return httpx.Response(status_code=200, json={"items": [{"id": "x"}]})

    monkeypatch.setattr(client._client, "request", fake_request)
    caplog.set_level(logging.DEBUG, logger="nerm.http")
    _ = client.request("GET", "/profiles", json={"hello": "world"})
    messages = [record.getMessage() for record in caplog.records if record.name == "nerm.http"]
    assert any("request method=GET path=/profiles" in msg for msg in messages)
    assert any("url=https://tenant.example.com/profiles" in msg for msg in messages)
    assert any("headers={'Authorization': '<redacted>'}" in msg for msg in messages)
    assert all("Bearer token" not in msg for msg in messages)
    assert any("response method=GET path=/profiles" in msg for msg in messages)
    assert all("response_body" not in msg for msg in messages)
    get_settings.cache_clear()


def test_http_client_logs_body_when_debug_enabled(monkeypatch, caplog) -> None:
    monkeypatch.setenv("NERM_DEBUG_LOG_BODIES", "1")
    monkeypatch.setenv("NERM_TRACE_MAX_BYTES", "64")
    get_settings.cache_clear()
    client = NermHttpClient(base_url="https://tenant.example.com", bearer_token="Bearer token")

    def fake_request(method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        return httpx.Response(status_code=200, json={"items": [{"id": "x"}]})

    monkeypatch.setattr(client._client, "request", fake_request)
    caplog.set_level(logging.DEBUG, logger="nerm.http")
    _ = client.request("GET", "/profiles", json={"hello": "x" * 500})
    messages = [record.getMessage() for record in caplog.records if record.name == "nerm.http"]
    assert any("req_body=" in msg for msg in messages)
    assert any("response_body method=GET path=/profiles body=" in msg for msg in messages)
    assert any("<truncated>" in msg for msg in messages)
    get_settings.cache_clear()


def test_http_client_request_response_logs_visible_at_info_level(monkeypatch, caplog) -> None:
    monkeypatch.setenv("NERM_DEBUG_LOG_BODIES", "0")
    get_settings.cache_clear()
    caplog.set_level(logging.INFO, logger="nerm.http")
    client = NermHttpClient(base_url="https://tenant.example.com", bearer_token="Bearer token")

    def fake_request(method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        return httpx.Response(status_code=200, json={"items": []})

    monkeypatch.setattr(client._client, "request", fake_request)
    _ = client.request("GET", "/users")
    messages = [record.getMessage() for record in caplog.records if record.name == "nerm.http"]
    assert any("tenant_connection base_url=https://tenant.example.com" in msg for msg in messages)
    assert any("request method=GET path=/users" in msg for msg in messages)
    assert any("response method=GET path=/users" in msg for msg in messages)
    get_settings.cache_clear()
