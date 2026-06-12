from nerm.errors import NermApiError
from nerm.tools.delegations import (
    nerm_create_delegation,
    nerm_delete_delegation,
    nerm_get_delegation,
    nerm_list_delegations,
    nerm_update_delegation,
)


def test_list_delegations_respects_circuit_breaker(monkeypatch) -> None:
    calls = {"n": 0}

    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        calls["n"] += 1
        return {"items": [{"id": f"delegation-{calls['n']}-{i}"} for i in range(100)]}

    monkeypatch.setattr("nerm.tools.delegations.NermHttpClient.request", fake_request)
    result = nerm_list_delegations(limit=6000, nerm_base_url="https://tenant.example.com", nerm_bearer_token="Bearer token")
    assert result["pages_fetched"] == 50
    assert result["pagination_limited"] is True
    assert len(result["items"]) == 5000


def test_get_delegation_maps_error(monkeypatch) -> None:
    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        raise NermApiError(status=404, body="not found")

    monkeypatch.setattr("nerm.tools.delegations.NermHttpClient.request", fake_request)
    result = nerm_get_delegation("missing", "https://tenant.example.com", "Bearer token")
    assert result == {"error": "nerm_api_error", "status": 404, "body": "not found"}


def test_create_update_delete_delegation_contract(monkeypatch) -> None:
    calls: list[tuple[str, str, object]] = []

    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        calls.append((method, path, json))
        return {"id": "delegation-1", "method": method}

    monkeypatch.setattr("nerm.tools.delegations.NermHttpClient.request", fake_request)
    payload = {
        "delegator_user_id": "8d9580a3-279d-48cc-a6a2-4ea561f6c62a",
        "delegate_user_id": "f4d1f3e0-1ad1-4f53-aa2a-5bf02417ab9e",
    }
    created = nerm_create_delegation(payload, "https://tenant.example.com", "Bearer token")
    updated = nerm_update_delegation("delegation-1", payload, "https://tenant.example.com", "Bearer token")
    deleted = nerm_delete_delegation("delegation-1", "https://tenant.example.com", "Bearer token")
    assert "delegation" in created
    assert created["delegation"]["id"] == "delegation-1"
    assert "delegation" in updated
    assert updated["delegation"]["id"] == "delegation-1"
    assert deleted["id"] == "delegation-1"
    assert deleted["method"] == "DELETE"
    assert (
        "POST",
        "/delegations",
        {"delegation": {"delegator_id": "8d9580a3-279d-48cc-a6a2-4ea561f6c62a", "delegate_id": "f4d1f3e0-1ad1-4f53-aa2a-5bf02417ab9e"}},
    ) in calls
    assert (
        "PATCH",
        "/delegations/delegation-1",
        {"delegation": {"delegator_id": "8d9580a3-279d-48cc-a6a2-4ea561f6c62a", "delegate_id": "f4d1f3e0-1ad1-4f53-aa2a-5bf02417ab9e"}},
    ) in calls


def test_create_delegation_accepts_pre_wrapped_payload(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        captured["json"] = json
        return {"id": "delegation-1"}

    monkeypatch.setattr("nerm.tools.delegations.NermHttpClient.request", fake_request)
    result = nerm_create_delegation(
        {
            "delegation": {
                "delegator_user_id": "8d9580a3-279d-48cc-a6a2-4ea561f6c62a",
                "delegate_user_id": "f4d1f3e0-1ad1-4f53-aa2a-5bf02417ab9e",
            }
        },
        "https://tenant.example.com",
        "Bearer token",
    )
    assert result["delegation"]["id"] == "delegation-1"
    assert captured["json"] == {
        "delegation": {
            "delegator_id": "8d9580a3-279d-48cc-a6a2-4ea561f6c62a",
            "delegate_id": "f4d1f3e0-1ad1-4f53-aa2a-5bf02417ab9e",
        }
    }


def test_create_delegation_normalizes_wrapped_response(monkeypatch) -> None:
    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        return {"delegation": {"id": 7, "delegator_id": 8, "delegate_id": 9}}

    monkeypatch.setattr("nerm.tools.delegations.NermHttpClient.request", fake_request)
    result = nerm_create_delegation(
        {
            "delegator_user_id": "8d9580a3-279d-48cc-a6a2-4ea561f6c62a",
            "delegate_user_id": "f4d1f3e0-1ad1-4f53-aa2a-5bf02417ab9e",
        },
        "https://tenant.example.com",
        "Bearer token",
    )
    assert result["delegation"]["id"] == "7"
    assert result["delegation"]["delegator_id"] == "8"
    assert result["delegation"]["delegate_id"] == "9"


def test_create_delegation_rejects_invalid_payload() -> None:
    result = nerm_create_delegation(
        {"delegate_user_id": "not-enough-fields"},
        "https://tenant.example.com",
        "Bearer token",
    )
    assert result["error"] == "invalid_delegation_spec"
    assert "details" in result


def test_update_delegation_normalizes_expiration(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        captured["json"] = json
        return {"id": "delegation-1"}

    monkeypatch.setattr("nerm.tools.delegations.NermHttpClient.request", fake_request)
    result = nerm_update_delegation(
        "delegation-1",
        {
            "delegator_id": "8d9580a3-279d-48cc-a6a2-4ea561f6c62a",
            "delegatee_id": "f4d1f3e0-1ad1-4f53-aa2a-5bf02417ab9e",
            "expiration": "2026-12-31T23:59:59Z",
        },
        "https://tenant.example.com",
        "Bearer token",
    )
    assert result["delegation"]["id"] == "delegation-1"
    assert captured["json"] == {
        "delegation": {
            "delegator_id": "8d9580a3-279d-48cc-a6a2-4ea561f6c62a",
            "delegate_id": "f4d1f3e0-1ad1-4f53-aa2a-5bf02417ab9e",
            "expiration": "2026-12-31T23:59:59+00:00",
        }
    }


def test_create_delegation_accepts_noncanonical_expiration_keys(monkeypatch) -> None:
    base_payload = {
        "delegator_user_id": "8d9580a3-279d-48cc-a6a2-4ea561f6c62a",
        "delegate_user_id": "f4d1f3e0-1ad1-4f53-aa2a-5bf02417ab9e",
    }
    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        return {"id": "delegation-1"}

    monkeypatch.setattr("nerm.tools.delegations.NermHttpClient.request", fake_request)
    for key in ("end_date", "expires_at", "expiration_date"):
        result = nerm_create_delegation(
            {**base_payload, key: "2026-06-30"},
            "https://tenant.example.com",
            "Bearer token",
        )
        assert "delegation" in result


def test_update_delegation_allows_partial_payload_and_expiration(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        captured["json"] = json
        return {"id": "delegation-1"}

    monkeypatch.setattr("nerm.tools.delegations.NermHttpClient.request", fake_request)
    result = nerm_update_delegation(
        "delegation-1",
        {"expiration": "2026-06-30T00:00:00Z"},
        "https://tenant.example.com",
        "Bearer token",
    )
    assert result["delegation"]["id"] == "delegation-1"
    assert captured["json"] == {"delegation": {"expiration": "2026-06-30T00:00:00+00:00"}}


def test_create_delegation_date_only_expiration_uses_current_time_of_day(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        captured["json"] = json
        return {"id": "delegation-1"}

    monkeypatch.setattr("nerm.tools.delegations.NermHttpClient.request", fake_request)
    result = nerm_create_delegation(
        {
            "delegator_id": "8d9580a3-279d-48cc-a6a2-4ea561f6c62a",
            "delegate_id": "f4d1f3e0-1ad1-4f53-aa2a-5bf02417ab9e",
            "expiration": "2026-06-30",
        },
        "https://tenant.example.com",
        "Bearer token",
    )
    assert result["delegation"]["id"] == "delegation-1"
    expiration = captured["json"]["delegation"]["expiration"]  # type: ignore[index]
    assert str(expiration).startswith("2026-06-30T")


def test_update_delegation_date_only_expiration_uses_current_time_of_day(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        captured["json"] = json
        return {"id": "delegation-1"}

    monkeypatch.setattr("nerm.tools.delegations.NermHttpClient.request", fake_request)
    result = nerm_update_delegation(
        "delegation-1",
        {"expiration": "2026-07-01"},
        "https://tenant.example.com",
        "Bearer token",
    )
    assert result["delegation"]["id"] == "delegation-1"
    expiration = captured["json"]["delegation"]["expiration"]  # type: ignore[index]
    assert str(expiration).startswith("2026-07-01T")


def test_create_delegation_maps_expiration_error_with_guidance(monkeypatch) -> None:
    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        raise NermApiError(status=400, body='{"errors":["Expiration must be after today"]}')

    monkeypatch.setattr("nerm.tools.delegations.NermHttpClient.request", fake_request)
    result = nerm_create_delegation(
        {
            "delegator_user_id": "8d9580a3-279d-48cc-a6a2-4ea561f6c62a",
            "delegate_user_id": "f4d1f3e0-1ad1-4f53-aa2a-5bf02417ab9e",
            "expiration": "2030-03-01T00:00:00Z",
        },
        "https://tenant.example.com",
        "Bearer token",
    )
    assert result["error"] == "invalid_delegation_spec"
    assert result["guidance"]["preferred_input"] == "expiration"


def test_update_delegation_accepts_noncanonical_expiration_keys(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        captured["json"] = json
        return {"id": "delegation-1"}

    monkeypatch.setattr("nerm.tools.delegations.NermHttpClient.request", fake_request)
    result = nerm_update_delegation(
        "delegation-1",
        {"expiration_date": "2026-07-05T00:00:00Z"},
        "https://tenant.example.com",
        "Bearer token",
    )
    assert result["delegation"]["id"] == "delegation-1"
    assert captured["json"] == {"delegation": {"expiration": "2026-07-05T00:00:00+00:00"}}


def test_create_delegation_prevalidates_past_expiration_without_api_call(monkeypatch) -> None:
    called = {"value": False}

    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        called["value"] = True
        return {"id": "delegation-1"}

    monkeypatch.setattr("nerm.tools.delegations.NermHttpClient.request", fake_request)
    result = nerm_create_delegation(
        {
            "delegator_user_id": "8d9580a3-279d-48cc-a6a2-4ea561f6c62a",
            "delegate_user_id": "f4d1f3e0-1ad1-4f53-aa2a-5bf02417ab9e",
            "expiration": "2020-01-01T00:00:00Z",
        },
        "https://tenant.example.com",
        "Bearer token",
    )
    assert called["value"] is False
    assert result["error"] == "invalid_delegation_spec"
    assert result["guidance"]["preferred_input"] == "expiration"
    assert "current_time_utc" in result["guidance"]
    assert "example_30_days_utc" in result["guidance"]


def test_update_delegation_normalizes_wrapped_response(monkeypatch) -> None:
    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        return {"delegation": {"id": 7, "delegator_id": 8, "delegate_id": 9}}

    monkeypatch.setattr("nerm.tools.delegations.NermHttpClient.request", fake_request)
    result = nerm_update_delegation(
        "delegation-1",
        {
            "delegator_user_id": "8d9580a3-279d-48cc-a6a2-4ea561f6c62a",
            "delegate_user_id": "f4d1f3e0-1ad1-4f53-aa2a-5bf02417ab9e",
        },
        "https://tenant.example.com",
        "Bearer token",
    )
    assert result["delegation"]["id"] == "7"
    assert result["delegation"]["delegator_id"] == "8"
    assert result["delegation"]["delegate_id"] == "9"


def test_delete_delegation_returns_api_payload(monkeypatch) -> None:
    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        return {"status": "ok"}

    monkeypatch.setattr("nerm.tools.delegations.NermHttpClient.request", fake_request)
    result = nerm_delete_delegation("delegation-1", "https://tenant.example.com", "Bearer token")
    assert result == {"status": "ok"}


def test_get_delegation_normalizes_id_fields_to_string(monkeypatch) -> None:
    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        return {"id": 1, "delegator_id": 2, "delegate_id": 3}

    monkeypatch.setattr("nerm.tools.delegations.NermHttpClient.request", fake_request)
    result = nerm_get_delegation("1", "https://tenant.example.com", "Bearer token")
    assert result["id"] == "1"
    assert result["delegator_id"] == "2"
    assert result["delegate_id"] == "3"


def test_list_delegations_rejects_invalid_pagination_type() -> None:
    result = nerm_list_delegations(
        limit="invalid",  # type: ignore[arg-type]
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert result["error"] == "invalid_pagination_spec"


def test_list_delegations_reads_delegations_key(monkeypatch) -> None:
    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        return {"delegations": [{"id": "d-1"}]}

    monkeypatch.setattr("nerm.tools.delegations.NermHttpClient.request", fake_request)
    result = nerm_list_delegations(limit=10, nerm_base_url="https://tenant.example.com", nerm_bearer_token="Bearer token")
    assert result["items"][0]["id"] == "d-1"
    assert "delegator_name" in result["items"][0]
    assert "delegate_name" in result["items"][0]


def test_list_delegations_can_include_user_details(monkeypatch) -> None:
    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        if path == "/delegations":
            return {
                "delegations": [
                    {"id": "d-1", "delegator_id": "u-1", "delegate_id": "u-2"},
                    {"id": "d-2", "delegator_id": "u-1", "delegate_id": "u-3"},
                ]
            }
        if path == "/users/u-1":
            return {"id": "u-1", "name": "Delegator One", "login": "d1", "email": "d1@example.com"}
        if path == "/users/u-2":
            return {"id": "u-2", "name": "Delegate Two", "login": "d2", "email": "d2@example.com"}
        if path == "/users/u-3":
            return {"id": "u-3", "name": "Delegate Three", "login": "d3", "email": "d3@example.com"}
        raise AssertionError(f"unexpected path: {path}")

    monkeypatch.setattr("nerm.tools.delegations.NermHttpClient.request", fake_request)
    result = nerm_list_delegations(
        limit=10,
        include_user_details=True,
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert result["items"][0]["delegator_name"] == "Delegator One"
    assert result["items"][0]["delegator_login"] == "d1"
    assert result["items"][0]["delegator_email"] == "d1@example.com"
    assert result["items"][0]["delegate_name"] == "Delegate Two"
    assert result["items"][1]["delegate_name"] == "Delegate Three"


def test_list_delegations_includes_user_details_by_default(monkeypatch) -> None:
    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        if path == "/delegations":
            return {"delegations": [{"id": "d-1", "delegator_id": "u-1", "delegate_id": "u-2"}]}
        if path == "/users/u-1":
            return {"id": "u-1", "name": "Delegator One", "login": "d1", "email": "d1@example.com"}
        if path == "/users/u-2":
            return {"id": "u-2", "name": "Delegate Two", "login": "d2", "email": "d2@example.com"}
        raise AssertionError(f"unexpected path: {path}")

    monkeypatch.setattr("nerm.tools.delegations.NermHttpClient.request", fake_request)
    result = nerm_list_delegations(limit=10, nerm_base_url="https://tenant.example.com", nerm_bearer_token="Bearer token")
    assert result["items"][0]["delegator_name"] == "Delegator One"
    assert result["items"][0]["delegate_name"] == "Delegate Two"


def test_list_delegations_enrichment_handles_wrapped_user_payloads(monkeypatch) -> None:
    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        if path == "/delegations":
            return {"delegations": [{"id": "d-1", "delegator_id": "u-1", "delegate_id": "u-2"}]}
        if path == "/users/u-1":
            return {"user": {"id": "u-1", "display_name": "Delegator One", "uid": "d1", "mail": "d1@example.com"}}
        if path == "/users/u-2":
            return {"users": [{"id": "u-2", "full_name": "Delegate Two", "username": "d2", "email": "d2@example.com"}]}
        raise AssertionError(f"unexpected path: {path}")

    monkeypatch.setattr("nerm.tools.delegations.NermHttpClient.request", fake_request)
    result = nerm_list_delegations(limit=10, nerm_base_url="https://tenant.example.com", nerm_bearer_token="Bearer token")
    assert result["items"][0]["delegator_name"] == "Delegator One"
    assert result["items"][0]["delegator_login"] == "d1"
    assert result["items"][0]["delegate_name"] == "Delegate Two"
    assert result["items"][0]["delegate_login"] == "d2"
