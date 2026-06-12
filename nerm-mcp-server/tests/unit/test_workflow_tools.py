from nerm.errors import NermApiError
from nerm.tools.workflow import (
    nerm_add_department_via_workflow,
    nerm_add_location_via_workflow,
    nerm_add_organization_via_workflow,
    nerm_get_job_status,
    nerm_get_workflow_session,
    nerm_list_workflow_session_statuses,
    nerm_list_workflow_sessions,
)


def test_list_workflow_sessions_respects_breaker(monkeypatch) -> None:
    calls = {"n": 0}

    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        calls["n"] += 1
        return {"items": [{"id": f"wf-{calls['n']}-{i}"} for i in range(100)]}

    monkeypatch.setattr("nerm.tools.workflow.NermHttpClient.request", fake_request)
    result = nerm_list_workflow_sessions(limit=6000, nerm_base_url="https://tenant.example.com", nerm_bearer_token="Bearer token")
    assert result["pages_fetched"] == 50
    assert result["pagination_limited"] is True


def test_get_workflow_session_maps_error(monkeypatch) -> None:
    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        raise NermApiError(status=404, body="missing")

    monkeypatch.setattr("nerm.tools.workflow.NermHttpClient.request", fake_request)
    result = nerm_get_workflow_session("missing", "https://tenant.example.com", "Bearer token")
    assert result == {"error": "nerm_api_error", "status": 404, "body": "missing"}


def test_workflow_submit_contract(monkeypatch) -> None:
    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        return {"workflow_session_full_id": "wf-123", "status": "Pending"}

    monkeypatch.setattr("nerm.tools.workflow.NermHttpClient.request", fake_request)
    payload = {"name": "test", "workflow_id": "wf-template"}
    for fn in (nerm_add_location_via_workflow, nerm_add_department_via_workflow, nerm_add_organization_via_workflow):
        result = fn(payload, "https://tenant.example.com", "Bearer token")
        assert result["message"] == "request submitted"
        assert result["status"] == "Pending"
        assert result["workflow_session_full_id"] == "wf-123"


def test_workflow_status_and_job_happy_path(monkeypatch) -> None:
    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        if "job_status" in path:
            return {"id": "job-1", "status": "Pending"}
        return {"items": [{"status": "Pending"}]}

    monkeypatch.setattr("nerm.tools.workflow.NermHttpClient.request", fake_request)
    statuses = nerm_list_workflow_session_statuses(10, 0, False, "https://tenant.example.com", "Bearer token")
    assert "error" not in statuses
    job = nerm_get_job_status("job-1", "https://tenant.example.com", "Bearer token")
    assert job["id"] == "job-1"


def test_workflow_sessions_invalid_status_type_returns_schema_error() -> None:
    result = nerm_list_workflow_sessions(
        limit=10,
        offset=0,
        status="DoesNotExist",  # type: ignore[arg-type]
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert result["error"] == "nerm_api_error"


def test_workflow_sessions_accepts_valid_status(monkeypatch) -> None:
    seen_params: list[dict | None] = []

    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        seen_params.append(params)
        if "offset" in (params or {}) and params.get("offset") == 0 and "status" not in (params or {}):
            return {"items": [{"status": "Pending"}]}
        return {"items": [{"id": "wf-1", "status": "Pending"}]}

    monkeypatch.setattr("nerm.tools.workflow.NermHttpClient.request", fake_request)
    result = nerm_list_workflow_sessions(
        limit=10,
        offset=0,
        status="Pending",
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert "error" not in result
    assert any((params or {}).get("status") == "Pending" for params in seen_params)


def test_workflow_sessions_normalize_id_to_string(monkeypatch) -> None:
    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        return {"workflow_sessions": [{"id": 7001, "status": "Pending"}]}

    monkeypatch.setattr("nerm.tools.workflow.NermHttpClient.request", fake_request)
    result = nerm_list_workflow_sessions(
        limit=10,
        offset=0,
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert result["items"][0]["id"] == "7001"


def test_workflow_sessions_reject_invalid_pagination_type() -> None:
    result = nerm_list_workflow_sessions(
        limit="invalid",  # type: ignore[arg-type]
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert result["error"] == "invalid_pagination_spec"


def test_get_job_status_normalizes_ids_to_string(monkeypatch) -> None:
    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        return {"id": 901, "status": "Pending"}

    monkeypatch.setattr("nerm.tools.workflow.NermHttpClient.request", fake_request)
    result = nerm_get_job_status("12345", "https://tenant.example.com", "Bearer token")
    assert result["id"] == "901"
    assert result["requested_job_id"] == "12345"


def test_workflow_statuses_reject_invalid_pagination_type() -> None:
    result = nerm_list_workflow_session_statuses(
        limit="invalid",  # type: ignore[arg-type]
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert result["error"] == "invalid_pagination_spec"
