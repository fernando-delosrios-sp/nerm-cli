import json
import os

from nerm.client.endpoints import AUDIT_EVENTS_QUERY
from nerm.client.http_client import NermHttpClient
from nerm.errors import NermApiError
from nerm.schemas.common import normalize_pagination, pagination_validation_error
from nerm.schemas.audit import AuditQueryPayload, normalize_audit_event_item
from nerm.services.pagination import collect_paginated_items, unique_item_count
from nerm.spec_contract import (
    AUDIT_ALLOWED_FILTER_KEYS,
    AUDIT_API_METHOD_EVENT_TYPES,
    AUDIT_EVENT_TYPES,
    AUDIT_SUBJECT_TYPES,
    MAX_AUDIT_FILTERS,
)
from nerm.tools.param_specs import ForceAllFlag, Int32NonNegative, Int32Positive, OptionalBaseUrl, OptionalBearerToken
from nerm.tools._reference_catalog import execute_with_nerm_error_json, extract_list_records, resolve_connection
from pydantic import ValidationError


def _load_audit_filter_enums() -> dict[str, list[str]]:
    raw = os.getenv("NERM_AUDIT_FILTER_ENUMS_JSON", "").strip()
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}
    enums: dict[str, list[str]] = {}
    for key, values in payload.items():
        if not isinstance(key, str) or not isinstance(values, list):
            continue
        normalized = [str(v) for v in values if isinstance(v, (str, int, float))]
        if normalized:
            enums[key] = normalized
    return enums


def nerm_query_audit_events(
    subject_type: str | None = None,
    event_type: str | None = None,
    subject_id: str | None = None,
    workflow_name: str | None = None,
    workflow_uid: str | None = None,
    workflow_profile_type: str | None = None,
    profile_type: str | None = None,
    filters: dict[str, object] | None = None,
    limit: Int32Positive = 100,
    offset: Int32NonNegative = 0,
    force_all: ForceAllFlag = True,
    nerm_base_url: OptionalBaseUrl = None,
    nerm_bearer_token: OptionalBearerToken = None,
) -> dict:
    """Query audit events with validated filter keys and explicit API-spec guidance.

    Use for historical action/event analysis, not current profile state retrieval.
    Route change-history intents here: "what changed", "who changed", "when changed",
    "updated by", and audit/event trail questions.
    API-spec common core values:
    - subject_type: WorkflowSession, Profile
    - event_type/type: Get, Post, Patch, Delete (`event_type` maps to payload key `type`)
    Note: API supports additional subject/event domains; these are common examples,
    not an exhaustive closed enum.
    Allowed filter keys: subject_type, type, subject_id, workflow_name,
    workflow_uid, workflow_profile_type, profile_type.
    Compatibility guidance:
    - workflow_name/workflow_uid/workflow_profile_type are workflow-session oriented filters.
    - profile_type is profile-oriented.
    - For workflow history by label/name/uid, prefer subject_type=WorkflowSession with
      workflow_uid (or workflow_name). Avoid subject_id as the primary workflow filter.
    - Prefer 1-3 selective filters before adding broad text filters.
    - API allows at most 5 non-pagination filters.
    Pagination:
    - Default behavior traverses all pages from `offset` and returns the full audit trail.
    - Set `force_all=false` to cap the response to `limit` records (default page-sized behavior).
    For "what are valid audit types?" questions, use the response fields
    `allowed_subject_type_values` and `allowed_event_type_values` as authoritative.
    Example calls:
    - Workflow-session deletes: subject_type=WorkflowSession, event_type=Delete
    - Profile events for one profile: subject_type=Profile, subject_id=<profile_id>
    - Workflow by uid: subject_type=WorkflowSession, filters={"workflow_uid": "<uid>"}
    """
    def _is_no_audit_events_found_error(exc: NermApiError) -> bool:
        if exc.status not in {400, 404}:
            return False
        body_text = str(exc.body or "").lower()
        return "no audit" in body_text and "found" in body_text

    def _run() -> dict:
        try:
            bounded_limit, bounded_offset = normalize_pagination(limit=limit, offset=offset)
        except ValidationError as exc:
            return pagination_validation_error(exc)
        base_url, bearer_token = resolve_connection(nerm_base_url=nerm_base_url, nerm_bearer_token=nerm_bearer_token)
        client = NermHttpClient(base_url=base_url, bearer_token=bearer_token)
        audit_filter_query: dict[str, object] = {}
        if subject_type:
            audit_filter_query["subject_type"] = subject_type
        if event_type:
            audit_filter_query["type"] = event_type
        invalid_core_values: dict[str, dict[str, object]] = {}
        if "subject_type" in audit_filter_query and str(audit_filter_query["subject_type"]) not in AUDIT_SUBJECT_TYPES:
            invalid_core_values["subject_type"] = {
                "provided": str(audit_filter_query["subject_type"]),
                "allowed_values": list(AUDIT_SUBJECT_TYPES),
            }
        allowed_event_type_values = (*AUDIT_API_METHOD_EVENT_TYPES, *AUDIT_EVENT_TYPES)
        if "type" in audit_filter_query and str(audit_filter_query["type"]) not in allowed_event_type_values:
            invalid_core_values["type"] = {
                "provided": str(audit_filter_query["type"]),
                "allowed_values": list(allowed_event_type_values),
            }
        if invalid_core_values:
            return {
                "error": "invalid_audit_query_spec",
                "message": "One or more audit core values are not allowed by API-spec value lists.",
                "invalid_values": invalid_core_values,
                "allowed_subject_type_values": list(AUDIT_SUBJECT_TYPES),
                "allowed_event_type_values": list(allowed_event_type_values),
            }
        if subject_id:
            audit_filter_query["subject_id"] = subject_id
        if workflow_name:
            audit_filter_query["workflow_name"] = workflow_name
        if workflow_uid:
            audit_filter_query["workflow_uid"] = workflow_uid
        if workflow_profile_type:
            audit_filter_query["workflow_profile_type"] = workflow_profile_type
        if profile_type:
            audit_filter_query["profile_type"] = profile_type
        if filters:
            # Backward compatibility path: keep supporting raw filter maps.
            invalid = [key for key in filters.keys() if key not in AUDIT_ALLOWED_FILTER_KEYS]
            if invalid:
                return {
                    "error": "invalid_audit_query_spec",
                    "message": f"Unsupported audit filters: {sorted(invalid)}",
                    "allowed_filters": list(AUDIT_ALLOWED_FILTER_KEYS),
                    "allowed_subject_type_values": list(AUDIT_SUBJECT_TYPES),
                    "allowed_event_type_values": list(allowed_event_type_values),
                }
            # Explicit named arguments take precedence over deprecated filters map.
            for key, value in filters.items():
                if key in audit_filter_query:
                    continue
                audit_filter_query[key] = value
        filter_enums = _load_audit_filter_enums()
        invalid_enum_values: dict[str, dict[str, object]] = {}
        for key, value in audit_filter_query.items():
            if key not in filter_enums:
                continue
            allowed_values = filter_enums[key]
            value_str = str(value)
            if value_str not in allowed_values:
                invalid_enum_values[key] = {
                    "provided": value_str,
                    "allowed_values": allowed_values,
                }
        if invalid_enum_values:
            return {
                "error": "invalid_audit_query_spec",
                "message": "One or more audit filter values are outside the configured enum set.",
                "invalid_values": invalid_enum_values,
                "allowed_subject_type_values": list(AUDIT_SUBJECT_TYPES),
                "allowed_event_type_values": list(allowed_event_type_values),
            }
        filter_count = len(list(audit_filter_query.keys()))
        if filter_count > MAX_AUDIT_FILTERS:
            return {
                "error": "invalid_audit_query_spec",
                "message": f"A maximum of {MAX_AUDIT_FILTERS} audit filters is allowed.",
                "filter_count": filter_count,
                "allowed_subject_type_values": list(AUDIT_SUBJECT_TYPES),
                "allowed_event_type_values": list(allowed_event_type_values),
            }

        def _fetch_page(page_offset: int, page_limit: int, _pages: int, _collected: int) -> object:
            audit_query: dict[str, object] = {
                "limit": page_limit,
                "offset": page_offset,
            }
            if audit_filter_query:
                audit_query["filters"] = dict(audit_filter_query)
            try:
                validated = AuditQueryPayload.model_validate(audit_query).model_dump(exclude_none=True)
            except ValidationError as exc:
                return {
                    "error": "invalid_audit_query_spec",
                    "message": "audit query failed schema validation.",
                    "details": exc.errors(include_url=False),
                }
            body = {"audit_events": validated}
            try:
                return client.request("POST", AUDIT_EVENTS_QUERY, timeout=15.0, json=body)
            except NermApiError as exc:
                # Treat offset overflow/empty slices as end-of-pagination.
                if _is_no_audit_events_found_error(exc):
                    return {"audit_events": []}
                raise

        def _parse_page(payload: object) -> list[dict]:
            if not isinstance(payload, dict):
                return []
            if payload.get("error") == "invalid_audit_query_spec":
                return []
            page_items = extract_list_records(payload, preferred_keys=("audit_events",))
            return [normalize_audit_event_item(item) for item in page_items]

        effective_limit = bounded_limit
        # Default full-trail mode: when caller uses default limit, remove the retrieval window cap.
        # Keep explicit caller limits intact so bounded sampling remains possible with force_all=true.
        if force_all and bounded_limit == 100:
            effective_limit = 2_147_483_647

        items, pages, pagination_limited, total_count, confirmation_needed = collect_paginated_items(
            bounded_limit=effective_limit,
            bounded_offset=bounded_offset,
            force_all=force_all,
            fetch_page=_fetch_page,
            parse_page_items=_parse_page,
        )
        if confirmation_needed:
            confirmation_needed["allowed_subject_type_values"] = list(AUDIT_SUBJECT_TYPES)
            confirmation_needed["allowed_event_type_values"] = list(allowed_event_type_values)
            return confirmation_needed

        response = {
            "items": items,
            "limit": effective_limit,
            "offset": bounded_offset,
            "pages_fetched": pages,
            "pagination_limited": pagination_limited,
            "returned_count": len(items),
            "unique_item_count": unique_item_count(items),
            "allowed_subject_type_values": list(AUDIT_SUBJECT_TYPES),
            "allowed_event_type_values": list(allowed_event_type_values),
        }
        if total_count is not None:
            response["total"] = total_count
        return response

    return execute_with_nerm_error_json(_run)
