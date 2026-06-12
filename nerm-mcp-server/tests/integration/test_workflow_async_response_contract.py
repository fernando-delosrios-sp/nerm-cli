from nerm.tools.workflow import nerm_add_location_via_workflow


def test_workflow_submit_contract(monkeypatch) -> None:
    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        return {"workflow_session_full_id": "wf-1", "status": "Pending"}

    monkeypatch.setattr("nerm.tools.workflow.NermHttpClient.request", fake_request)
    result = nerm_add_location_via_workflow(
        {"workflow_id": "wf-template"},
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert result["message"] == "request submitted"
    assert result["status"] == "Pending"
    assert result["workflow_session_full_id"] == "wf-1"
