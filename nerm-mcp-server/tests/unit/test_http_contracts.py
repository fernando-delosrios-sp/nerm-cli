from nerm.tools.advanced_search import nerm_run_advanced_search
from nerm.tools.audit import nerm_query_audit_events
from nerm.tools.delegations import nerm_create_delegation, nerm_update_delegation
from nerm.tools.identity_proofing import nerm_list_identity_proofing_results
from nerm.tools.workflow import nerm_add_location_via_workflow, nerm_get_job_status


def test_advanced_search_contract(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        captured["method"] = method
        captured["path"] = path
        captured["json"] = json
        return {"items": []}

    monkeypatch.setattr("nerm.tools.advanced_search.NermHttpClient.request", fake_request)
    nerm_run_advanced_search(
        {"condition_rules_attributes": [{"type": "ProfileStatusRule", "comparison_operator": "==", "value": "Active"}]},
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert captured["method"] == "POST"
    assert captured["path"] == "/advanced_search/run"
    assert captured["json"] == {
        "advanced_search": {"condition_rules_attributes": [{"type": "ProfileStatusRule", "comparison_operator": "==", "value": "Active"}]}
    }


def test_audit_query_contract(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        captured["method"] = method
        captured["path"] = path
        captured["json"] = json
        return {"items": []}

    monkeypatch.setattr("nerm.tools.audit.NermHttpClient.request", fake_request)
    nerm_query_audit_events(
        subject_type="WorkflowSession",
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert captured["method"] == "POST"
    assert captured["path"] == "/audit_events/query"
    assert "audit_events" in captured["json"]


def test_delegation_write_contracts(monkeypatch) -> None:
    calls: list[tuple[str, str, object]] = []

    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        calls.append((method, path, json))
        return {"id": "d1"}

    monkeypatch.setattr("nerm.tools.delegations.NermHttpClient.request", fake_request)
    nerm_create_delegation(
        {"delegator_user_id": "8d9580a3-279d-48cc-a6a2-4ea561f6c62a", "delegate_user_id": "f4d1f3e0-1ad1-4f53-aa2a-5bf02417ab9e"},
        "https://tenant.example.com",
        "Bearer token",
    )
    nerm_update_delegation(
        "d1",
        {"delegator_id": "8d9580a3-279d-48cc-a6a2-4ea561f6c62a", "delegate_id": "f4d1f3e0-1ad1-4f53-aa2a-5bf02417ab9e"},
        "https://tenant.example.com",
        "Bearer token",
    )
    assert (
        "POST",
        "/delegations",
        {"delegation": {"delegator_id": "8d9580a3-279d-48cc-a6a2-4ea561f6c62a", "delegate_id": "f4d1f3e0-1ad1-4f53-aa2a-5bf02417ab9e"}},
    ) in calls
    assert (
        "PATCH",
        "/delegations/d1",
        {"delegation": {"delegator_id": "8d9580a3-279d-48cc-a6a2-4ea561f6c62a", "delegate_id": "f4d1f3e0-1ad1-4f53-aa2a-5bf02417ab9e"}},
    ) in calls


def test_identity_proofing_contract(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        captured["method"] = method
        captured["path"] = path
        return {"items": []}

    monkeypatch.setattr("nerm.tools.identity_proofing.NermHttpClient.request", fake_request)
    nerm_list_identity_proofing_results(
        limit=10,
        offset=0,
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert captured["method"] == "GET"
    assert captured["path"] == "/identity_proofing_results"


def test_workflow_contracts(monkeypatch) -> None:
    calls: list[tuple[str, str]] = []

    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        calls.append((method, path))
        if path == "/job_status":
            return {"status": "Pending"}
        return {"workflow_session_full_id": "wf-1", "status": "Pending"}

    monkeypatch.setattr("nerm.tools.workflow.NermHttpClient.request", fake_request)
    nerm_add_location_via_workflow(
        {"workflow_id": "wf-template"},
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    nerm_get_job_status("job-1", "https://tenant.example.com", "Bearer token")
    assert ("POST", "/workflow_sessions") in calls
    assert ("GET", "/job_status") in calls
