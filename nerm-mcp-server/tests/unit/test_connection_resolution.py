import pytest

from nerm.config import get_settings
from nerm.tools._reference_catalog import normalize_base_url, resolve_connection


def test_normalize_base_url_appends_api_path_when_missing() -> None:
    normalized = normalize_base_url("https://tenant.example.com", "/api")
    assert normalized == "https://tenant.example.com/api"


def test_normalize_base_url_preserves_existing_path() -> None:
    normalized = normalize_base_url("https://tenant.example.com/custom/path", "/api")
    assert normalized == "https://tenant.example.com/custom/path"


def test_normalize_base_url_replaces_root_path() -> None:
    normalized = normalize_base_url("https://tenant.example.com/", "/api")
    assert normalized == "https://tenant.example.com/api"


def test_resolve_connection_uses_overrides_and_normalizes() -> None:
    get_settings.cache_clear()
    base_url, token = resolve_connection(
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert base_url == "https://tenant.example.com/api"
    assert token == "Bearer token"


def test_resolve_connection_raises_for_missing_credentials(monkeypatch) -> None:
    for name in ("NERM_BASE_URL", "NERM_TENANT", "NERM_BEARER_TOKEN", "NERM_API_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    get_settings.cache_clear()
    with pytest.raises(ValueError) as excinfo:
        resolve_connection()
    assert str(excinfo.value) == "NERM base URL and bearer token are required."
