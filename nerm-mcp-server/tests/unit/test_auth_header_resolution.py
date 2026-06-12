import logging

from nerm.auth import _redact_header_value, resolve_auth
from nerm.config import Settings


def test_auth_prefers_headers() -> None:
    settings = Settings(NERM_BASE_URL="https://fallback", NERM_BEARER_TOKEN="fallback-token")
    headers = {"X-NERM-Authorization": "header-token", "X-NERM-URL": "https://tenant"}
    auth = resolve_auth(headers, settings)
    assert auth.bearer_token == "header-token"
    assert auth.base_url == "https://tenant/api"


def test_auth_fallback_uses_settings_and_normalizes_base_url() -> None:
    settings = Settings(NERM_BASE_URL="https://fallback.example.com", NERM_BEARER_TOKEN="fallback-token")
    auth = resolve_auth({}, settings)
    assert auth.bearer_token == "fallback-token"
    assert auth.base_url == "https://fallback.example.com/api"


def test_auth_strips_whitespace_from_header_values() -> None:
    settings = Settings(NERM_BASE_URL="https://fallback.example.com", NERM_BEARER_TOKEN="fallback-token")
    headers = {"X-NERM-Authorization": "  header-token  ", "X-NERM-URL": "  https://tenant.example.com  "}
    auth = resolve_auth(headers, settings)
    assert auth.bearer_token == "header-token"
    assert auth.base_url == "https://tenant.example.com/api"


def test_auth_supports_bedrock_runtime_custom_headers() -> None:
    settings = Settings(NERM_BASE_URL="https://fallback.example.com", NERM_BEARER_TOKEN="fallback-token")
    headers = {
        "X-Amzn-Bedrock-AgentCore-Runtime-Custom-NERM-Authorization": "runtime-token",
        "X-Amzn-Bedrock-AgentCore-Runtime-Custom-NERM-URL": "https://tenant-runtime.example.com",
    }
    auth = resolve_auth(headers, settings)
    assert auth.bearer_token == "runtime-token"
    assert auth.base_url == "https://tenant-runtime.example.com/api"


def test_auth_header_url_with_existing_path_is_not_rewritten() -> None:
    settings = Settings(NERM_BASE_URL="https://fallback.example.com", NERM_BEARER_TOKEN="fallback-token")
    headers = {"X-NERM-Authorization": "header-token", "X-NERM-URL": "https://tenant.example.com/custom"}
    auth = resolve_auth(headers, settings)
    assert auth.base_url == "https://tenant.example.com/custom"


def test_auth_supports_case_insensitive_header_names() -> None:
    settings = Settings(NERM_BASE_URL="https://fallback.example.com", NERM_BEARER_TOKEN="fallback-token")
    headers = {
        "x-nerm-authorization": "header-token",
        "x-nerm-url": "https://tenant-lower.example.com",
    }
    auth = resolve_auth(headers, settings)
    assert auth.bearer_token == "header-token"
    assert auth.base_url == "https://tenant-lower.example.com/api"


def test_redact_header_value_masks_sensitive_values() -> None:
    assert _redact_header_value("Authorization", "Bearer abc123") == "<redacted>"
    assert _redact_header_value("X-Api-Token", "abc123") == "<redacted>"
    assert _redact_header_value("X-NERM-URL", "https://tenant.example.com") == "https://tenant.example.com"


def test_auth_logs_x_nerm_headers_with_masked_token(caplog) -> None:
    settings = Settings(NERM_BASE_URL="https://fallback.example.com", NERM_BEARER_TOKEN="fallback-token")
    headers = {
        "X-NERM-Authorization": "header-token-secret",
        "X-NERM-URL": "https://tenant.example.com",
    }
    with caplog.at_level(logging.DEBUG, logger="nerm.auth"):
        resolve_auth(headers, settings)
    assert "incoming_nerm_headers" in caplog.text
    assert "X-NERM-Authorization" in caplog.text
    assert "<redacted>" in caplog.text
    assert "header-token-secret" not in caplog.text
    assert "X-NERM-URL" in caplog.text
    assert "https://tenant.example.com" in caplog.text


def test_auth_logs_bedrock_nerm_headers_with_masked_token(caplog) -> None:
    settings = Settings(NERM_BASE_URL="https://fallback.example.com", NERM_BEARER_TOKEN="fallback-token")
    headers = {
        "X-Amzn-Bedrock-AgentCore-Runtime-Custom-NERM-Authorization": "runtime-token-secret",
        "X-Amzn-Bedrock-AgentCore-Runtime-Custom-NERM-URL": "https://tenant-runtime.example.com",
    }
    with caplog.at_level(logging.DEBUG, logger="nerm.auth"):
        resolve_auth(headers, settings)
    assert "X-Amzn-Bedrock-AgentCore-Runtime-Custom-NERM-Authorization" in caplog.text
    assert "<redacted>" in caplog.text
    assert "runtime-token-secret" not in caplog.text
    assert "X-Amzn-Bedrock-AgentCore-Runtime-Custom-NERM-URL" in caplog.text


def test_auth_logs_headers_at_info_when_verbose_trace_enabled(caplog) -> None:
    settings = Settings(
        NERM_BASE_URL="https://fallback.example.com",
        NERM_BEARER_TOKEN="fallback-token",
        NERM_VERBOSE_TRACE=True,
    )
    headers = {
        "X-NERM-Authorization": "header-token-secret",
        "X-NERM-URL": "https://tenant.example.com",
    }
    with caplog.at_level(logging.INFO, logger="nerm.auth"):
        resolve_auth(headers, settings)
    assert "incoming_nerm_headers" in caplog.text
