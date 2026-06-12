import os
import json

import pytest

from nerm.client import endpoints
from nerm.client.http_client import NermHttpClient
from nerm.config import get_settings
from nerm.schemas.advanced_search import AdvancedSearchPayload
from nerm.tools.advanced_search import nerm_run_advanced_search
from nerm.tools import _reference_catalog
from nerm.tools.attributes import nerm_get_attribute, nerm_list_attributes
from nerm.tools.audit import nerm_query_audit_events
from nerm.tools.delegations import nerm_create_delegation, nerm_list_delegations
from nerm.tools.identity_proofing import nerm_list_identity_proofing_results
from nerm.tools.profile_types import nerm_get_profile_type, nerm_list_profile_types
from nerm.tools.profiles import nerm_get_profile, nerm_list_profiles
from nerm.tools.roles import nerm_list_role_profiles, nerm_list_roles
from nerm.tools.users import (
    nerm_get_user,
    nerm_list_user_managers,
    nerm_list_user_profiles,
    nerm_list_user_roles,
    nerm_list_users,
)
from nerm.tools.workflow import nerm_add_location_via_workflow, nerm_list_workflow_session_statuses, nerm_list_workflow_sessions


def _tenant_base_url() -> str:
    settings = get_settings()
    return (
        os.getenv("NERM_BASE_URL", "").strip()
        or os.getenv("NERM_TENANT", "").strip()
        or settings.nerm_base_url.strip()
    )


def _tenant_token() -> str:
    settings = get_settings()
    return (
        os.getenv("NERM_BEARER_TOKEN", "").strip()
        or os.getenv("NERM_API_TOKEN", "").strip()
        or settings.nerm_bearer_token.strip()
    )


def _skip_if_no_real_tenant() -> None:
    if not _tenant_base_url() or not _tenant_token():
        pytest.skip("Set NERM_BASE_URL/NERM_BEARER_TOKEN (or NERM_TENANT/NERM_API_TOKEN) to run real tenant smoke tests.")


def _reset_reference_cache() -> None:
    _reference_catalog._reference_cache = None


def _env_truthy(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _assert_no_tool_error(result: dict, tool_name: str, expected_route: str, base_url: str) -> None:
    if "error" not in result:
        return
    status = result.get("status")
    body = result.get("body")
    pytest.fail(
        (
            f"{tool_name} failed against live tenant. "
            f"expected_route={expected_route} base_url={base_url} status={status} body={body}"
        )
    )


def _is_known_safe_delegation_conflict(result: dict) -> bool:
    if result.get("error") != "nerm_api_error" or result.get("status") != 400:
        return False
    raw_body = result.get("body")
    if not isinstance(raw_body, str) or not raw_body.strip():
        return False
    try:
        body = json.loads(raw_body)
    except json.JSONDecodeError:
        return False
    errors = body.get("errors")
    if not isinstance(errors, list):
        return False
    text = " ".join(str(item).lower() for item in errors)
    return "already been delegated" in text


@pytest.mark.integration
def test_real_tenant_profile_types_and_attributes_smoke(monkeypatch: pytest.MonkeyPatch) -> None:
    _skip_if_no_real_tenant()
    _reset_reference_cache()
    base_url = _tenant_base_url()
    token = _tenant_token()

    original_request = NermHttpClient.request
    request_count = {"value": 0}

    def wrapped_request(self: NermHttpClient, method: str, path: str, **kwargs: object) -> dict:
        request_count["value"] += 1
        return original_request(self, method, path, **kwargs)

    monkeypatch.setattr(NermHttpClient, "request", wrapped_request)

    first_profile_types = nerm_list_profile_types(limit=5, offset=0, nerm_base_url=base_url, nerm_bearer_token=token)
    _assert_no_tool_error(first_profile_types, "nerm_list_profile_types", endpoints.PROFILE_TYPES, base_url)
    assert isinstance(first_profile_types.get("items"), list)
    calls_after_first = request_count["value"]
    assert calls_after_first >= 1

    second_profile_types = nerm_list_profile_types(limit=5, offset=0, nerm_base_url=base_url, nerm_bearer_token=token)
    _assert_no_tool_error(second_profile_types, "nerm_list_profile_types", endpoints.PROFILE_TYPES, base_url)
    assert request_count["value"] == calls_after_first

    first_attributes = nerm_list_attributes(limit=5, offset=0, nerm_base_url=base_url, nerm_bearer_token=token)
    _assert_no_tool_error(first_attributes, "nerm_list_attributes", endpoints.ATTRIBUTES, base_url)
    assert isinstance(first_attributes.get("items"), list)

    if first_profile_types["items"]:
        profile_type_id = first_profile_types["items"][0]["id"]
        profile_type = nerm_get_profile_type(profile_type_id, nerm_base_url=base_url, nerm_bearer_token=token)
        assert profile_type.get("id") == profile_type_id

    if first_attributes["items"]:
        attribute_id = first_attributes["items"][0]["id"]
        attribute = nerm_get_attribute(attribute_id, nerm_base_url=base_url, nerm_bearer_token=token)
        assert attribute.get("id") == attribute_id


@pytest.mark.integration
def test_real_tenant_profiles_and_users_smoke() -> None:
    _skip_if_no_real_tenant()
    base_url = _tenant_base_url()
    token = _tenant_token()

    profiles = nerm_list_profiles(limit=20, offset=0, nerm_base_url=base_url, nerm_bearer_token=token)
    _assert_no_tool_error(profiles, "nerm_list_profiles", endpoints.PROFILES, base_url)
    assert isinstance(profiles.get("items"), list)
    assert profiles.get("pages_fetched", 0) >= 1

    users = nerm_list_users(limit=20, offset=0, nerm_base_url=base_url, nerm_bearer_token=token)
    _assert_no_tool_error(users, "nerm_list_users", endpoints.USERS, base_url)
    assert isinstance(users.get("items"), list)
    assert users.get("pages_fetched", 0) >= 1


@pytest.mark.integration
def test_real_tenant_delegations_and_workflow_reads_smoke() -> None:
    _skip_if_no_real_tenant()
    base_url = _tenant_base_url()
    token = _tenant_token()

    delegations = nerm_list_delegations(limit=20, offset=0, nerm_base_url=base_url, nerm_bearer_token=token)
    _assert_no_tool_error(delegations, "nerm_list_delegations", endpoints.DELEGATIONS, base_url)
    assert isinstance(delegations.get("items"), list)

    workflow_statuses = nerm_list_workflow_session_statuses(
        limit=20, offset=0, nerm_base_url=base_url, nerm_bearer_token=token
    )
    _assert_no_tool_error(workflow_statuses, "nerm_list_workflow_session_statuses", endpoints.WORKFLOW_SESSIONS, base_url)
    assert isinstance(workflow_statuses.get("items"), list)

    workflow_sessions = nerm_list_workflow_sessions(limit=20, offset=0, nerm_base_url=base_url, nerm_bearer_token=token)
    _assert_no_tool_error(workflow_sessions, "nerm_list_workflow_sessions", endpoints.WORKFLOW_SESSIONS, base_url)
    assert isinstance(workflow_sessions.get("items"), list)

    identity_proofing = nerm_list_identity_proofing_results(
        limit=20, offset=0, nerm_base_url=base_url, nerm_bearer_token=token
    )
    _assert_no_tool_error(
        identity_proofing,
        "nerm_list_identity_proofing_results",
        endpoints.IDENTITY_PROOFING_RESULTS,
        base_url,
    )
    assert isinstance(identity_proofing.get("items"), list)


@pytest.mark.integration
def test_real_tenant_audit_query_smoke() -> None:
    _skip_if_no_real_tenant()
    base_url = _tenant_base_url()
    token = _tenant_token()
    # Keep query narrow and read-only.
    audit = nerm_query_audit_events(
        subject_type="WorkflowSession",
        limit=5,
        offset=0,
        nerm_base_url=base_url,
        nerm_bearer_token=token,
    )
    _assert_no_tool_error(audit, "nerm_query_audit_events", endpoints.AUDIT_EVENTS_QUERY, base_url)
    assert isinstance(audit.get("items", []), list)


@pytest.mark.integration
def test_real_tenant_advanced_search_smoke_guarded() -> None:
    _skip_if_no_real_tenant()
    if not _env_truthy("NERM_SMOKE_ENABLE_ADVANCED_SEARCH"):
        pytest.skip("Set NERM_SMOKE_ENABLE_ADVANCED_SEARCH=1 to run advanced-search smoke test.")
    raw = os.getenv("NERM_SMOKE_ADVANCED_SEARCH_JSON", "").strip()
    if not raw:
        pytest.skip("Set NERM_SMOKE_ADVANCED_SEARCH_JSON to a constrained advanced_search inner JSON payload.")
    try:
        inner = json.loads(raw)
    except json.JSONDecodeError as exc:
        pytest.fail(f"NERM_SMOKE_ADVANCED_SEARCH_JSON is invalid JSON: {exc}")
        return
    if not isinstance(inner, dict):
        pytest.fail("NERM_SMOKE_ADVANCED_SEARCH_JSON must parse to a JSON object.")
        return
    try:
        AdvancedSearchPayload.validate_inner_payload(inner)
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"NERM_SMOKE_ADVANCED_SEARCH_JSON failed advanced search schema validation: {exc}")
        return
    base_url = _tenant_base_url()
    token = _tenant_token()
    result = nerm_run_advanced_search(
        advanced_search=inner,
        nerm_base_url=base_url,
        nerm_bearer_token=token,
    )
    _assert_no_tool_error(result, "nerm_run_advanced_search", endpoints.ADVANCED_SEARCH_RUN, base_url)


@pytest.mark.integration
def test_real_tenant_roles_domain_smoke_guarded() -> None:
    _skip_if_no_real_tenant()
    if not _env_truthy("NERM_SMOKE_ENABLE_ROLES"):
        pytest.skip("Set NERM_SMOKE_ENABLE_ROLES=1 to run roles-domain smoke test.")
    base_url = _tenant_base_url()
    token = _tenant_token()

    roles = nerm_list_roles(limit=20, offset=0, nerm_base_url=base_url, nerm_bearer_token=token)
    _assert_no_tool_error(roles, "nerm_list_roles", endpoints.ROLES, base_url)
    assert isinstance(roles.get("items"), list)

    user_roles = nerm_list_user_roles(limit=20, offset=0, nerm_base_url=base_url, nerm_bearer_token=token)
    _assert_no_tool_error(user_roles, "nerm_list_user_roles", endpoints.USER_ROLES, base_url)
    assert isinstance(user_roles.get("items"), list)

    user_managers = nerm_list_user_managers(limit=20, offset=0, nerm_base_url=base_url, nerm_bearer_token=token)
    _assert_no_tool_error(user_managers, "nerm_list_user_managers", endpoints.USER_MANAGERS, base_url)
    assert isinstance(user_managers.get("items"), list)

    user_profiles = nerm_list_user_profiles(limit=20, offset=0, nerm_base_url=base_url, nerm_bearer_token=token)
    _assert_no_tool_error(user_profiles, "nerm_list_user_profiles", endpoints.USER_PROFILES, base_url)
    assert isinstance(user_profiles.get("items"), list)

    role_profiles = nerm_list_role_profiles(limit=20, offset=0, nerm_base_url=base_url, nerm_bearer_token=token)
    _assert_no_tool_error(role_profiles, "nerm_list_role_profiles", endpoints.ROLE_PROFILES, base_url)
    assert isinstance(role_profiles.get("items"), list)


@pytest.mark.integration
def test_real_tenant_get_by_id_smoke_guarded() -> None:
    _skip_if_no_real_tenant()
    if not _env_truthy("NERM_SMOKE_ENABLE_GET_BY_ID"):
        pytest.skip("Set NERM_SMOKE_ENABLE_GET_BY_ID=1 to run get-by-id smoke test.")
    base_url = _tenant_base_url()
    token = _tenant_token()

    profiles = nerm_list_profiles(limit=5, offset=0, nerm_base_url=base_url, nerm_bearer_token=token)
    _assert_no_tool_error(profiles, "nerm_list_profiles", endpoints.PROFILES, base_url)
    if profiles.get("items"):
        profile_id = profiles["items"][0].get("id")
        if profile_id:
            profile = nerm_get_profile(profile_id, nerm_base_url=base_url, nerm_bearer_token=token)
            _assert_no_tool_error(profile, "nerm_get_profile", f"{endpoints.PROFILES}/:id", base_url)

    users = nerm_list_users(limit=5, offset=0, nerm_base_url=base_url, nerm_bearer_token=token)
    _assert_no_tool_error(users, "nerm_list_users", endpoints.USERS, base_url)
    if users.get("items"):
        user_id = users["items"][0].get("id")
        if user_id:
            user = nerm_get_user(user_id, nerm_base_url=base_url, nerm_bearer_token=token)
            _assert_no_tool_error(user, "nerm_get_user", f"{endpoints.USERS}/:id", base_url)


@pytest.mark.integration
def test_real_tenant_write_smoke_guarded() -> None:
    _skip_if_no_real_tenant()
    if not _env_truthy("NERM_SMOKE_ENABLE_WRITES"):
        pytest.skip("Set NERM_SMOKE_ENABLE_WRITES=1 to run write smoke test.")
    base_url = _tenant_base_url()
    token = _tenant_token()

    delegation_raw = os.getenv("NERM_SMOKE_CREATE_DELEGATION_JSON", "").strip()
    workflow_raw = os.getenv("NERM_SMOKE_WORKFLOW_SUBMIT_JSON", "").strip()
    if not delegation_raw and not workflow_raw:
        pytest.skip(
            "Provide at least one payload via NERM_SMOKE_CREATE_DELEGATION_JSON or NERM_SMOKE_WORKFLOW_SUBMIT_JSON."
        )

    if delegation_raw:
        try:
            delegation_payload = json.loads(delegation_raw)
        except json.JSONDecodeError as exc:
            pytest.fail(f"NERM_SMOKE_CREATE_DELEGATION_JSON is invalid JSON: {exc}")
            return
        if not isinstance(delegation_payload, dict):
            pytest.fail("NERM_SMOKE_CREATE_DELEGATION_JSON must parse to a JSON object.")
            return
        delegation_result = nerm_create_delegation(
            delegation_payload,
            nerm_base_url=base_url,
            nerm_bearer_token=token,
        )
        if _is_known_safe_delegation_conflict(delegation_result):
            pytest.skip("Delegation already exists for the provided pair; treating as idempotent write smoke.")
        _assert_no_tool_error(delegation_result, "nerm_create_delegation", endpoints.DELEGATIONS, base_url)
        assert delegation_result.get("request_submitted") is True

    if workflow_raw:
        try:
            workflow_payload = json.loads(workflow_raw)
        except json.JSONDecodeError as exc:
            pytest.fail(f"NERM_SMOKE_WORKFLOW_SUBMIT_JSON is invalid JSON: {exc}")
            return
        if not isinstance(workflow_payload, dict):
            pytest.fail("NERM_SMOKE_WORKFLOW_SUBMIT_JSON must parse to a JSON object.")
            return
        workflow_result = nerm_add_location_via_workflow(
            workflow_payload,
            nerm_base_url=base_url,
            nerm_bearer_token=token,
        )
        _assert_no_tool_error(workflow_result, "nerm_add_location_via_workflow", endpoints.WORKFLOW_SESSIONS, base_url)
        assert workflow_result.get("message") == "request submitted"
