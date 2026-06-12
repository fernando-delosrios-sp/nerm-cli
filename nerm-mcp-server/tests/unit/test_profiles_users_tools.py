from nerm.errors import NermApiError
from nerm.tools.profiles import nerm_get_profile, nerm_list_profiles
from nerm.tools.users import nerm_examine_jwt_user, nerm_get_user, nerm_list_users


def test_list_profiles_force_all_bypasses_circuit_breaker(monkeypatch) -> None:
    call_count = {"n": 0}

    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        call_count["n"] += 1
        return {"items": [{"id": f"profile-{call_count['n']}-{i}"} for i in range(100)]}

    monkeypatch.setattr("nerm.tools.profiles.NermHttpClient.request", fake_request)
    result = nerm_list_profiles(
        limit=500,
        force_all=True,
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert result["pages_fetched"] == 5
    assert result["pagination_limited"] is False
    assert len(result["items"]) == 500


def test_list_users_force_all_bypasses_breaker(monkeypatch) -> None:
    calls = {"n": 0}
    pages = [
        {"users": [{"id": f"user-1-{i}"} for i in range(100)]},
        {"users": [{"id": f"user-2-{i}"} for i in range(100)]},
        {"users": [{"id": f"user-3-{i}"} for i in range(100)]},
        {"users": [{"id": f"user-4-{i}"} for i in range(100)]},
        {"users": []},
    ]

    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        current = pages[calls["n"]]
        calls["n"] += 1
        return current

    monkeypatch.setattr("nerm.tools.users.NermHttpClient.request", fake_request)
    result = nerm_list_users(
        limit=200,
        force_all=True,
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert result["pagination_limited"] is False
    assert result["pages_fetched"] == 2
    assert len(result["items"]) == 200


def test_list_users_supports_legacy_items_key(monkeypatch) -> None:
    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        return {"items": [{"id": "user-legacy"}]}

    monkeypatch.setattr("nerm.tools.users.NermHttpClient.request", fake_request)
    result = nerm_list_users(
        limit=10,
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert result["items"][0]["id"] == "user-legacy"


def test_list_users_uses_total_metadata_to_fetch_short_final_pages(monkeypatch) -> None:
    pages = [
        {"users": [{"id": f"user-1-{i}"} for i in range(80)], "total": 250},
        {"users": [{"id": f"user-2-{i}"} for i in range(80)], "total": 250},
        {"users": [{"id": f"user-3-{i}"} for i in range(40)], "total": 250},
        {"users": [{"id": f"user-4-{i}"} for i in range(50)], "total": 250},
    ]
    calls = {"n": 0}

    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        current = pages[calls["n"]]
        calls["n"] += 1
        return current

    monkeypatch.setattr("nerm.tools.users.NermHttpClient.request", fake_request)
    result = nerm_list_users(
        limit=250,
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert calls["n"] == 4
    assert result["pages_fetched"] == 4
    assert len(result["items"]) == 250


def test_list_users_fallbacks_name_to_login_on_no_users_found(monkeypatch) -> None:
    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        if params and params.get("name") == "linda davis":
            raise NermApiError(status=400, body='{"error":"no users found"}')
        if params and params.get("login") == "linda.davis":
            return {"users": [{"id": "user-1", "login": "linda.davis"}]}
        raise AssertionError(f"unexpected params: {params}")

    monkeypatch.setattr("nerm.tools.users.NermHttpClient.request", fake_request)
    result = nerm_list_users(
        name="linda davis",
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert result["items"][0]["id"] == "user-1"


def test_list_users_fallbacks_email_localpart_to_login_on_no_users_found(monkeypatch) -> None:
    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        if params and params.get("email") == "alice.ford":
            raise NermApiError(status=400, body='{"error":"no users found"}')
        if params and params.get("login") == "alice.ford":
            return {"users": [{"id": "user-2", "login": "alice.ford"}]}
        raise AssertionError(f"unexpected params: {params}")

    monkeypatch.setattr("nerm.tools.users.NermHttpClient.request", fake_request)
    result = nerm_list_users(
        email="alice.ford",
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert result["items"][0]["id"] == "user-2"


def test_list_users_treats_no_users_found_as_end_of_pages(monkeypatch) -> None:
    calls = {"n": 0}

    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        del self, method, path, timeout, json, params
        if calls["n"] == 0:
            calls["n"] += 1
            return {"users": [{"id": "u-1"}], "total": 2}
        calls["n"] += 1
        raise NermApiError(status=400, body='{"error":"no users found"}')

    monkeypatch.setattr("nerm.tools.users.NermHttpClient.request", fake_request)
    result = nerm_list_users(
        limit=10,
        offset=0,
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert "error" not in result
    assert result["total"] == 2
    assert result["returned_count"] == 1


def test_get_profile_maps_api_error(monkeypatch) -> None:
    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        raise NermApiError(status=404, body="not found")

    monkeypatch.setattr("nerm.tools.profiles.NermHttpClient.request", fake_request)
    result = nerm_get_profile(
        "profile-404",
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert result == {"error": "nerm_api_error", "status": 404, "body": "not found"}


def test_get_user_happy_path(monkeypatch) -> None:
    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        return {"id": "user-123"}

    monkeypatch.setattr("nerm.tools.users.NermHttpClient.request", fake_request)
    result = nerm_get_user(
        "user-123",
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert result["id"] == "user-123"


def test_examine_jwt_user_missing_header(monkeypatch) -> None:
    monkeypatch.delenv("NERM_INVOKE_AUTHORIZATION", raising=False)
    result = nerm_examine_jwt_user()
    assert result["status"] == 400


def test_examine_jwt_user_handles_bearer_prefix_case_insensitively(monkeypatch) -> None:
    token = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJ1c2VyLTEyMyJ9."
    monkeypatch.setenv("NERM_INVOKE_AUTHORIZATION", f"bearer {token}")
    result = nerm_examine_jwt_user()
    assert "error" not in result
    assert result["claims"]["sub"] == "user-123"


def test_examine_jwt_user_rejects_empty_bearer_token(monkeypatch) -> None:
    monkeypatch.setenv("NERM_INVOKE_AUTHORIZATION", "Bearer   ")
    result = nerm_examine_jwt_user()
    assert result["status"] == 400
    assert "token is empty" in result["body"]


def test_list_users_rejects_invalid_pagination_type() -> None:
    result = nerm_list_users(
        limit="invalid",  # type: ignore[arg-type]
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert result["error"] == "invalid_pagination_spec"


def test_list_profiles_normalizes_id_to_string(monkeypatch) -> None:
    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        return {"items": [{"id": 123}]}

    monkeypatch.setattr("nerm.tools.profiles.NermHttpClient.request", fake_request)
    result = nerm_list_profiles(
        limit=10,
        offset=0,
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert result["items"][0]["id"] == "123"


def test_list_profiles_requires_confirmation_for_large_result_sets(monkeypatch) -> None:
    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        return {"items": [], "total": 6001}

    monkeypatch.setattr("nerm.tools.profiles.NermHttpClient.request", fake_request)
    result = nerm_list_profiles(
        limit=100,
        offset=0,
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert result["error"] == "confirmation_required"
    assert result["total"] == 6001


def test_list_profiles_treats_no_profiles_found_404_as_end_of_pages(monkeypatch) -> None:
    calls = {"n": 0}

    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        del self, method, path, timeout, json
        if calls["n"] == 0:
            calls["n"] += 1
            return {"items": [{"id": "p-1"}], "total": 2}
        calls["n"] += 1
        raise NermApiError(status=404, body='{"error":"no profiles found"}')

    monkeypatch.setattr("nerm.tools.profiles.NermHttpClient.request", fake_request)
    result = nerm_list_profiles(
        limit=10,
        offset=0,
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert "error" not in result
    assert result["total"] == 2
    assert result["returned_count"] == 1


def test_list_profiles_treats_no_profiles_found_400_as_end_of_pages(monkeypatch) -> None:
    calls = {"n": 0}

    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        del self, method, path, timeout, json
        if calls["n"] == 0:
            calls["n"] += 1
            return {"items": [{"id": "p-1"}], "total": 2}
        calls["n"] += 1
        raise NermApiError(status=400, body='{"error":"no profiles found"}')

    monkeypatch.setattr("nerm.tools.profiles.NermHttpClient.request", fake_request)
    result = nerm_list_profiles(
        limit=10,
        offset=0,
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert "error" not in result
    assert result["total"] == 2
    assert result["returned_count"] == 1


def test_list_profiles_derives_total_when_first_page_exactly_hits_limit(monkeypatch) -> None:
    calls = {"n": 0}

    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        del self, method, path, timeout, json, params
        if calls["n"] == 0:
            calls["n"] += 1
            return {"items": [{"id": f"p-{i}"} for i in range(100)]}
        if calls["n"] == 1:
            calls["n"] += 1
            return {"items": [{"id": "p-100"}]}
        calls["n"] += 1
        return {"items": []}

    monkeypatch.setattr("nerm.tools.profiles.NermHttpClient.request", fake_request)
    result = nerm_list_profiles(
        limit=100,
        offset=0,
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert "error" not in result
    assert result["returned_count"] == 100
    assert result["total"] == 101
