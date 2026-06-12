import importlib.util
from pathlib import Path


def _load_post_deploy_module():
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "post_deploy_check.py"
    spec = importlib.util.spec_from_file_location("post_deploy_check", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_run_post_deploy_check_success(monkeypatch) -> None:
    module = _load_post_deploy_module()
    monkeypatch.setattr(module, "load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.setattr(module, "check_required_runtime_env", lambda: [])
    monkeypatch.setattr(module, "has_any_tenant_credential_set", lambda: True)
    monkeypatch.setattr(module, "get_health_report", lambda: {"status": "ok", "tool_count": 1})
    monkeypatch.setattr(module, "evaluate_health_report", lambda report: (True, "healthy"))

    result = module.run_post_deploy_check()
    assert result.ok is True
    assert result.checks["missing_runtime_env"] == []
    assert result.checks["has_tenant_credentials"] is True


def test_run_post_deploy_check_failure(monkeypatch) -> None:
    module = _load_post_deploy_module()
    monkeypatch.setattr(module, "load_dotenv", lambda *args, **kwargs: None)
    monkeypatch.setattr(module, "check_required_runtime_env", lambda: ["NERM_API_BASE_PATH"])
    monkeypatch.setattr(module, "has_any_tenant_credential_set", lambda: False)
    monkeypatch.setattr(module, "get_health_report", lambda: {"status": "error"})
    monkeypatch.setattr(module, "evaluate_health_report", lambda report: (False, "health status is not ok"))

    result = module.run_post_deploy_check()
    assert result.ok is False
    assert result.checks["missing_runtime_env"] == ["NERM_API_BASE_PATH"]
    assert result.checks["has_tenant_credentials"] is False
