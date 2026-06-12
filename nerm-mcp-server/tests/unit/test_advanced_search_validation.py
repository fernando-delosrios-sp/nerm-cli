from nerm.tools.advanced_search import nerm_run_advanced_search


def test_advanced_search_rejects_sql_style() -> None:
    result = nerm_run_advanced_search({"field": "name", "operator": "eq"})
    assert result["error"] == "invalid_advanced_search_spec"


def test_advanced_search_wraps_payload_and_calls_spec_endpoint(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        captured["method"] = method
        captured["path"] = path
        captured["json"] = json
        return {"items": [{"id": "p1"}]}

    monkeypatch.setattr("nerm.tools.advanced_search.NermHttpClient.request", fake_request)
    inner = {
        "label": "my-search",
        "condition_rules_attributes": [{"type": "ProfileStatusRule", "comparison_operator": "==", "value": "Active"}],
    }
    result = nerm_run_advanced_search(
        inner,
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert "error" not in result
    assert captured["method"] == "POST"
    assert captured["path"] == "/advanced_search/run"
    assert captured["json"] == {"advanced_search": inner}


def test_advanced_search_rejects_empty_condition_rules() -> None:
    result = nerm_run_advanced_search(
        {"label": "too-broad", "condition_rules_attributes": []},
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert result["error"] == "insufficient_advanced_search_filters"
    assert "at least one condition rule" in result["message"]


def test_advanced_search_requires_condition_rules_attributes() -> None:
    result = nerm_run_advanced_search(
        {"label": "missing-rules"},
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert result["error"] == "invalid_advanced_search_spec"


def test_advanced_search_rejects_unsupported_rule_type() -> None:
    result = nerm_run_advanced_search(
        {
            "condition_rules_attributes": [
                {"type": "UnknownRule", "comparison_operator": "==", "value": "x"},
            ]
        },
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert result["error"] == "invalid_advanced_search_spec"
    assert "failed schema validation" in result["message"]


def test_advanced_search_rejects_invalid_profile_status_operator() -> None:
    result = nerm_run_advanced_search(
        {
            "condition_rules_attributes": [
                {"type": "ProfileStatusRule", "comparison_operator": "include?", "value": "Active"},
            ]
        },
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert result["error"] == "invalid_advanced_search_spec"
    assert "details" in result


def test_advanced_search_rejects_profile_attribute_rule_missing_required_fields() -> None:
    result = nerm_run_advanced_search(
        {
            "condition_rules_attributes": [
                {"type": "ProfileAttributeRule", "condition_object_type": "TextFieldAttribute", "comparison_operator": "=="},
            ]
        },
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert result["error"] == "invalid_advanced_search_spec"
    assert "details" in result


def test_advanced_search_rejects_symbolic_date_operators() -> None:
    result = nerm_run_advanced_search(
        {
            "condition_rules_attributes": [
                {
                    "type": "ProfileAttributeRule",
                    "condition_object_type": "DateAttribute",
                    "condition_object_id": "6f0fac52-44de-4f87-9909-5b5a5b8e7e2c",
                    "comparison_operator": ">",
                    "value": "2026-06-01",
                },
            ]
        },
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert result["error"] == "invalid_advanced_search_spec"
    assert "details" in result


def test_advanced_search_normalizes_profile_ids_in_response(monkeypatch) -> None:
    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        return {"items": [{"id": 501, "name": "Profile A"}]}

    monkeypatch.setattr("nerm.tools.advanced_search.NermHttpClient.request", fake_request)
    result = nerm_run_advanced_search(
        {"condition_rules_attributes": [{"type": "ProfileStatusRule", "comparison_operator": "==", "value": "Active"}]},
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert result["items"][0]["id"] == "501"
