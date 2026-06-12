import pytest

from nerm.tools.delegations import nerm_get_delegation, nerm_list_delegations
from nerm.tools.roles import (
    nerm_get_role,
    nerm_get_role_profile,
    nerm_list_role_profiles,
    nerm_list_roles,
)
from nerm.tools.users import (
    nerm_get_user_manager,
    nerm_get_user_profile,
    nerm_get_user_role,
    nerm_list_user_managers,
    nerm_list_user_profiles,
    nerm_list_user_roles,
)
from nerm.tools.workflow import (
    nerm_get_workflow_session,
    nerm_list_workflow_session_statuses,
    nerm_list_workflow_sessions,
)


BASE_URL = "https://tenant.example.com"
TOKEN = "Bearer token"


@pytest.mark.parametrize(
    ("tool_call", "expected_method", "expected_path"),
    [
        (lambda: nerm_list_delegations(limit=1, offset=0, nerm_base_url=BASE_URL, nerm_bearer_token=TOKEN), "GET", "/delegations"),
        (lambda: nerm_get_delegation("d1", nerm_base_url=BASE_URL, nerm_bearer_token=TOKEN), "GET", "/delegations/d1"),
        (lambda: nerm_list_roles(limit=1, offset=0, nerm_base_url=BASE_URL, nerm_bearer_token=TOKEN), "GET", "/roles"),
        (lambda: nerm_get_role("r1", nerm_base_url=BASE_URL, nerm_bearer_token=TOKEN), "GET", "/roles/r1"),
        (lambda: nerm_list_user_roles(limit=1, offset=0, nerm_base_url=BASE_URL, nerm_bearer_token=TOKEN), "GET", "/user_roles"),
        (lambda: nerm_get_user_role("ur1", nerm_base_url=BASE_URL, nerm_bearer_token=TOKEN), "GET", "/user_roles/ur1"),
        (lambda: nerm_list_user_managers(limit=1, offset=0, nerm_base_url=BASE_URL, nerm_bearer_token=TOKEN), "GET", "/user_managers"),
        (lambda: nerm_get_user_manager("um1", nerm_base_url=BASE_URL, nerm_bearer_token=TOKEN), "GET", "/user_managers/um1"),
        (lambda: nerm_list_user_profiles(limit=1, offset=0, nerm_base_url=BASE_URL, nerm_bearer_token=TOKEN), "GET", "/user_profiles"),
        (lambda: nerm_get_user_profile("up1", nerm_base_url=BASE_URL, nerm_bearer_token=TOKEN), "GET", "/user_profiles/up1"),
        (lambda: nerm_list_role_profiles(limit=1, offset=0, nerm_base_url=BASE_URL, nerm_bearer_token=TOKEN), "GET", "/role_profiles"),
        (lambda: nerm_get_role_profile("rp1", nerm_base_url=BASE_URL, nerm_bearer_token=TOKEN), "GET", "/role_profiles/rp1"),
        (lambda: nerm_list_workflow_sessions(limit=1, offset=0, nerm_base_url=BASE_URL, nerm_bearer_token=TOKEN), "GET", "/workflow_sessions"),
        (lambda: nerm_list_workflow_session_statuses(limit=1, offset=0, nerm_base_url=BASE_URL, nerm_bearer_token=TOKEN), "GET", "/workflow_sessions"),
    ],
)
def test_extended_http_contracts(monkeypatch, tool_call, expected_method, expected_path) -> None:
    captured: list[tuple[str, str]] = []

    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        captured.append((method, path))
        if path == "/workflow_sessions":
            return {"items": [{"id": "wf-1", "status": "Pending"}]}
        return {"items": [{"id": "x"}], "id": "x"}

    monkeypatch.setattr("nerm.client.http_client.NermHttpClient.request", fake_request)
    result = tool_call()
    assert "error" not in result
    assert (expected_method, expected_path) in captured


def test_workflow_get_session_lookup_uses_list_endpoint(monkeypatch) -> None:
    captured: list[tuple[str, str]] = []

    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        captured.append((method, path))
        return {"items": [{"id": "wf-123", "status": "Pending"}]}

    monkeypatch.setattr("nerm.client.http_client.NermHttpClient.request", fake_request)
    result = nerm_get_workflow_session("wf-123", nerm_base_url=BASE_URL, nerm_bearer_token=TOKEN)
    assert "error" not in result
    assert result["id"] == "wf-123"
    assert ("GET", "/workflow_sessions") in captured
