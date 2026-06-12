from nerm.tools.delegations import nerm_create_delegation


def test_write_tool_returns_request_submitted_contract(monkeypatch) -> None:
    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        return {"id": "delegation-1"}

    monkeypatch.setattr("nerm.tools.delegations.NermHttpClient.request", fake_request)
    result = nerm_create_delegation(
        {"delegator_user_id": "8d9580a3-279d-48cc-a6a2-4ea561f6c62a", "delegate_user_id": "f4d1f3e0-1ad1-4f53-aa2a-5bf02417ab9e"},
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert result["request_submitted"] is True
