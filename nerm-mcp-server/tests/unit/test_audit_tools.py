from nerm.tools.audit import nerm_query_audit_events


def test_audit_query_uses_spec_endpoint_and_payload(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        captured["method"] = method
        captured["path"] = path
        captured["json"] = json
        return {"items": []}

    monkeypatch.setattr("nerm.tools.audit.NermHttpClient.request", fake_request)
    result = nerm_query_audit_events(
        subject_type="WorkflowSession",
        event_type="Post",
        filters={"workflow_name": "Onboard"},
        limit=10,
        offset=5,
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert "error" not in result
    assert captured["method"] == "POST"
    assert captured["path"] == "/audit_events/query"
    payload = captured["json"]
    assert isinstance(payload, dict)
    inner = payload["audit_events"]
    assert inner["limit"] == 10
    assert inner["offset"] == 5
    assert inner["filters"]["subject_type"] == "WorkflowSession"
    assert inner["filters"]["type"] == "Post"
    assert inner["filters"]["workflow_name"] == "Onboard"
    assert "allowed_subject_type_values" in result
    assert "allowed_event_type_values" in result
    assert "WorkflowSession" in result["allowed_subject_type_values"]
    assert "AuditableProfileCreate" in result["allowed_event_type_values"]


def test_audit_query_supports_explicit_filter_params(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        captured["json"] = json
        return {"items": []}

    monkeypatch.setattr("nerm.tools.audit.NermHttpClient.request", fake_request)
    result = nerm_query_audit_events(
        subject_type="WorkflowSession",
        event_type="Get",
        workflow_uid="wf_uid_1",
        workflow_name="Onboard",
        workflow_profile_type="Assignments",
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert "error" not in result
    payload = captured["json"]
    assert isinstance(payload, dict)
    inner = payload["audit_events"]
    assert inner["filters"]["workflow_uid"] == "wf_uid_1"
    assert inner["filters"]["workflow_name"] == "Onboard"
    assert inner["filters"]["workflow_profile_type"] == "Assignments"


def test_audit_query_explicit_params_override_filters_map(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        captured["json"] = json
        return {"items": []}

    monkeypatch.setattr("nerm.tools.audit.NermHttpClient.request", fake_request)
    result = nerm_query_audit_events(
        workflow_uid="explicit_uid",
        filters={"workflow_uid": "legacy_uid"},
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert "error" not in result
    payload = captured["json"]
    assert isinstance(payload, dict)
    inner = payload["audit_events"]
    assert inner["filters"]["workflow_uid"] == "explicit_uid"


def test_audit_query_rejects_invalid_filters() -> None:
    result = nerm_query_audit_events(
        filters={"invalid_filter": "x"},
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert result["error"] == "invalid_audit_query_spec"
    assert "Email" in result["allowed_subject_type_values"]
    assert "AuditableProfileCreate" in result["allowed_event_type_values"]


def test_audit_query_rejects_unknown_subject_type_against_authoritative_list() -> None:
    result = nerm_query_audit_events(
        subject_type="UnknownSubjectType",
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert result["error"] == "invalid_audit_query_spec"
    assert "subject_type" in result["invalid_values"]


def test_audit_query_accepts_workflow_type_subject_type_from_spec_list(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        captured["json"] = json
        return {"audit_events": []}

    monkeypatch.setattr("nerm.tools.audit.NermHttpClient.request", fake_request)
    result = nerm_query_audit_events(
        subject_type="CreateWorkflow",
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert "error" not in result
    payload = captured["json"]
    assert isinstance(payload, dict)
    inner = payload["audit_events"]
    assert inner["filters"]["subject_type"] == "CreateWorkflow"


def test_audit_query_rejects_unknown_event_type_against_authoritative_list() -> None:
    result = nerm_query_audit_events(
        event_type="UnknownEventType",
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert result["error"] == "invalid_audit_query_spec"
    assert "type" in result["invalid_values"]


def test_audit_query_rejects_more_than_five_filters() -> None:
    result = nerm_query_audit_events(
        filters={
            "subject_type": "Profile",
            "type": "Get",
            "subject_id": "x",
            "workflow_name": "w",
            "workflow_uid": "u",
            "workflow_profile_type": "p",
        },
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert result["error"] == "invalid_audit_query_spec"


def test_audit_query_rejects_values_outside_configured_enums(monkeypatch) -> None:
    monkeypatch.setenv(
        "NERM_AUDIT_FILTER_ENUMS_JSON",
        '{"subject_type":["WorkflowSession","Profile"],"type":["Get","Post","Patch","Delete"]}',
    )
    result = nerm_query_audit_events(
        subject_type="UnknownType",
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert result["error"] == "invalid_audit_query_spec"
    assert "subject_type" in result["invalid_values"]


def test_audit_query_rejects_invalid_limit_type() -> None:
    result = nerm_query_audit_events(
        limit="bad",  # type: ignore[arg-type]
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert result["error"] == "invalid_pagination_spec"
    assert "details" in result


def test_audit_query_accepts_known_extended_subject_type_and_event_type(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        captured["json"] = json
        return {"items": []}

    monkeypatch.setattr("nerm.tools.audit.NermHttpClient.request", fake_request)
    result = nerm_query_audit_events(
        subject_type="Email",
        event_type="AuditableApiEvent",
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert "error" not in result
    payload = captured["json"]
    assert isinstance(payload, dict)
    inner = payload["audit_events"]
    assert inner["filters"]["subject_type"] == "Email"
    assert inner["filters"]["type"] == "AuditableApiEvent"


def test_audit_query_normalizes_event_id_to_string(monkeypatch) -> None:
    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        return {"items": [{"id": 77, "type": "Get"}]}

    monkeypatch.setattr("nerm.tools.audit.NermHttpClient.request", fake_request)
    result = nerm_query_audit_events(
        subject_type="WorkflowSession",
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert result["items"][0]["id"] == "77"


def test_audit_query_force_all_fetches_beyond_first_page(monkeypatch) -> None:
    offsets: list[int] = []

    def fake_request(self, method, path, timeout=15.0, json=None, params=None):  # noqa: ANN001
        assert method == "POST"
        assert path == "/audit_events/query"
        inner = json["audit_events"]
        page_offset = int(inner["offset"])
        page_limit = int(inner["limit"])
        offsets.append(page_offset)
        total = 101
        remaining = max(total - page_offset, 0)
        count = min(page_limit, remaining)
        events = [{"id": f"ev-{page_offset + i + 1}", "type": "Get"} for i in range(count)]
        return {"audit_events": events, "metadata": {"total": total}}

    monkeypatch.setattr("nerm.tools.audit.NermHttpClient.request", fake_request)
    result = nerm_query_audit_events(
        subject_type="WorkflowSession",
        force_all=True,
        nerm_base_url="https://tenant.example.com",
        nerm_bearer_token="Bearer token",
    )
    assert "error" not in result
    assert result["returned_count"] == 101
    assert result["total"] == 101
    assert result["pages_fetched"] == 2
    assert offsets == [0, 100]
