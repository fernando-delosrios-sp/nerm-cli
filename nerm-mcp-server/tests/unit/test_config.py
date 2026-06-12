from nerm.config import Settings


def test_defaults_load() -> None:
    settings = Settings()
    assert settings.log_level == "INFO"
    assert settings.nerm_static_reference_cache_ttl_sec == 3600
    assert settings.nerm_chart_include_base64 is False
    assert settings.nerm_debug_log_bodies is False
    assert settings.nerm_trace_max_bytes == 4096


def test_chart_base64_setting_parses_truthy(monkeypatch) -> None:
    monkeypatch.setenv("NERM_CHART_INCLUDE_BASE64", "1")
    settings = Settings()
    assert settings.nerm_chart_include_base64 is True


def test_debug_body_setting_and_trace_limit_parse(monkeypatch) -> None:
    monkeypatch.setenv("NERM_DEBUG_LOG_BODIES", "1")
    monkeypatch.setenv("NERM_TRACE_MAX_BYTES", "2048")
    settings = Settings()
    assert settings.nerm_debug_log_bodies is True
    assert settings.nerm_trace_max_bytes == 2048
