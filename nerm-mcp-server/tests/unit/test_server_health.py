import pytest

from nerm.health import get_health_report
from nerm.server import build_server


def test_server_health_report_contains_transport_and_tool_count() -> None:
    report = get_health_report()
    assert report["status"] == "ok"
    assert report["transport"] in {"stdio", "streamable-http"}
    assert isinstance(report["tool_count"], int)
    assert report["tool_count"] > 0


def test_build_server_rejects_invalid_api_base_path(monkeypatch) -> None:
    monkeypatch.setenv("NERM_API_BASE_PATH", "api")
    from nerm.config import get_settings

    get_settings.cache_clear()
    with pytest.raises(ValueError):
        build_server()
    get_settings.cache_clear()


def test_health_report_returns_error_when_server_bootstrap_fails(monkeypatch) -> None:
    def boom():  # noqa: ANN001
        raise ValueError("bad startup")

    monkeypatch.setattr("nerm.health.build_server", boom)
    report = get_health_report()
    assert report["status"] == "error"
    assert "bad startup" in str(report["error"])
