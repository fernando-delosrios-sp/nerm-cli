from nerm.errors import NermApiError
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


def test_list_roles_respects_circuit_breaker(monkeypatch) -> None:
    calls = {"n": 0}

    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        calls["n"] += 1
        return {"items": [{"id": f"role-{calls['n']}-{i}"} for i in range(100)]}

    monkeypatch.setattr("nerm.tools.roles.NermHttpClient.request", fake_request)
    result = nerm_list_roles(
        limit=6000,
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert result["pages_fetched"] == 50
    assert result["pagination_limited"] is True
    assert len(result["items"]) == 5000


def test_list_user_roles_force_all(monkeypatch) -> None:
    calls = {"n": 0}
    pages = [
        {"items": [{"id": f"ur-1-{i}"} for i in range(100)]},
        {"items": [{"id": f"ur-2-{i}"} for i in range(100)]},
        {"items": [{"id": f"ur-3-{i}"} for i in range(100)]},
        {"items": [{"id": f"ur-4-{i}"} for i in range(100)]},
        {"items": []},
    ]

    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        current = pages[calls["n"]]
        calls["n"] += 1
        return current

    monkeypatch.setattr("nerm.tools.roles.NermHttpClient.request", fake_request)
    result = nerm_list_user_roles(
        limit=200,
        force_all=True,
        include_user_details=False,
        include_role_details=False,
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert result["pagination_limited"] is False
    assert result["pages_fetched"] == 2
    assert len(result["items"]) == 200


def test_list_roles_uses_total_metadata_to_continue_after_short_page(monkeypatch) -> None:
    pages = [
        {"roles": [{"id": f"role-1-{i}"} for i in range(60)], "total": 180},
        {"roles": [{"id": f"role-2-{i}"} for i in range(60)], "total": 180},
        {"roles": [{"id": f"role-3-{i}"} for i in range(60)], "total": 180},
    ]
    calls = {"n": 0}

    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        current = pages[calls["n"]]
        calls["n"] += 1
        return current

    monkeypatch.setattr("nerm.tools.roles.NermHttpClient.request", fake_request)
    result = nerm_list_roles(
        limit=180,
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert calls["n"] == 3
    assert result["pages_fetched"] == 3
    assert len(result["items"]) == 180


def test_list_roles_treats_no_roles_found_as_end_of_pages(monkeypatch) -> None:
    calls = {"n": 0}

    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        del self, method, path, timeout, json, params
        if calls["n"] == 0:
            calls["n"] += 1
            return {"roles": [{"id": "r-1"}], "total": 2}
        calls["n"] += 1
        raise NermApiError(status=400, body='{"error":"no roles found"}')

    monkeypatch.setattr("nerm.tools.roles.NermHttpClient.request", fake_request)
    result = nerm_list_roles(
        limit=10,
        offset=0,
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert "error" not in result
    assert result["total"] == 2
    assert result["returned_count"] == 1


def test_list_user_roles_includes_user_details_by_default(monkeypatch) -> None:
    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        if path == "/user_roles":
            return {"user_roles": [{"id": "ur-1", "user_id": "u-1", "role_id": "r-1"}]}
        if path == "/users/u-1":
            return {"user": {"id": "u-1", "name": "User One", "login": "user.one", "email": "user.one@example.com"}}
        if path == "/roles/r-1":
            return {"role": {"id": "r-1", "name": "NERM Administrator", "uid": "nerm_admin", "private_role": False}}
        raise AssertionError(f"unexpected path {path}")

    monkeypatch.setattr("nerm.tools.roles.NermHttpClient.request", fake_request)
    result = nerm_list_user_roles(
        limit=10,
        offset=0,
        role_id="r-1",
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert result["items"][0]["user_name"] == "User One"
    assert result["items"][0]["user_login"] == "user.one"
    assert result["items"][0]["user_email"] == "user.one@example.com"
    assert result["items"][0]["role_name"] == "NERM Administrator"
    assert result["items"][0]["role_uid"] == "nerm_admin"


def test_get_role_maps_error(monkeypatch) -> None:
    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        raise NermApiError(status=404, body="not found")

    monkeypatch.setattr("nerm.tools.roles.NermHttpClient.request", fake_request)
    result = nerm_get_role("role-404", nerm_base_url="https://tenant.example.com", nerm_bearer_token="Bearer token")
    assert result == {"error": "nerm_api_error", "status": 404, "body": "not found"}


def test_related_getters_use_api(monkeypatch) -> None:
    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        return {"id": "ok"}

    monkeypatch.setattr("nerm.tools.roles.NermHttpClient.request", fake_request)

    assert nerm_get_user_role("a", "https://tenant.example.com", "Bearer token")["id"] == "ok"
    assert nerm_get_user_manager("a", "https://tenant.example.com", "Bearer token")["id"] == "ok"
    assert nerm_get_user_profile("a", "https://tenant.example.com", "Bearer token")["id"] == "ok"
    assert nerm_get_role_profile("a", "https://tenant.example.com", "Bearer token")["id"] == "ok"


def test_related_list_endpoints_happy_path(monkeypatch) -> None:
    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        key_by_path = {
            "/user_managers": "user_managers",
            "/user_profiles": "user_profiles",
            "/role_profiles": "role_profiles",
        }
        return {key_by_path[path]: [{"id": "x"}]}

    monkeypatch.setattr("nerm.tools.roles.NermHttpClient.request", fake_request)
    for fn in (nerm_list_user_managers, nerm_list_user_profiles, nerm_list_role_profiles):
        result = fn(limit=10, offset=0, nerm_base_url="https://tenant.example.com", nerm_bearer_token="Bearer token")
        assert "error" not in result
        assert result["items"] == [{"id": "x"}]


def test_list_roles_rejects_invalid_pagination_type() -> None:
    result = nerm_list_roles(
        limit="invalid",  # type: ignore[arg-type]
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert result["error"] == "invalid_pagination_spec"


def test_list_roles_rejects_unknown_query_argument() -> None:
    try:
        nerm_list_roles(
            nerm_base_url="https://tenant.example.com",
            nerm_bearer_token="Bearer token",
            query={"name": "NERM Administrator"},
        )
    except TypeError as exc:
        assert "query" in str(exc)
    else:
        raise AssertionError("Expected TypeError for unsupported query argument")


def test_get_role_normalizes_id_to_string(monkeypatch) -> None:
    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        return {"id": 987}

    monkeypatch.setattr("nerm.tools.roles.NermHttpClient.request", fake_request)
    result = nerm_get_role("role-1", nerm_base_url="https://tenant.example.com", nerm_bearer_token="Bearer token")
    assert result["id"] == "987"
