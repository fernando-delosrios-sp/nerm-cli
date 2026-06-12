from nerm.release_gate import (
    check_required_runtime_env,
    evaluate_health_report,
    has_any_tenant_credential_set,
)


def test_runtime_env_check_reports_missing_api_base_path() -> None:
    missing = check_required_runtime_env({})
    assert missing == ["NERM_API_BASE_PATH"]


def test_tenant_credential_set_detects_valid_pair() -> None:
    assert has_any_tenant_credential_set({"NERM_BASE_URL": "https://x", "NERM_BEARER_TOKEN": "Bearer t"}) is True
    assert has_any_tenant_credential_set({"NERM_TENANT": "https://x", "NERM_API_TOKEN": "Bearer t"}) is True
    assert has_any_tenant_credential_set({"NERM_BASE_URL": "https://x"}) is False


def test_evaluate_health_report_validates_status_and_tool_count() -> None:
    ok, _ = evaluate_health_report({"status": "ok", "tool_count": 1})
    assert ok is True
    ok, reason = evaluate_health_report({"status": "error"})
    assert ok is False
    assert "status is not ok" in reason
