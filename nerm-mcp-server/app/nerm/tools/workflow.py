from nerm.client.endpoints import (
    JOB_STATUS,
    WORKFLOW_SESSIONS,
)
from nerm.client.http_client import NermHttpClient
from nerm.config import get_settings
from nerm.schemas.common import normalize_pagination, pagination_validation_error
from nerm.schemas.workflow import normalize_job_status_payload, normalize_workflow_session_item
from nerm.services.pagination import (
    collect_paginated_items,
    unique_item_count,
)
from nerm.services.workflow_status import format_workflow_submission
from nerm.tools.param_specs import (
    ForceAllFlag,
    Int32NonNegative,
    Int32Positive,
    MetadataFlag,
    OptionalBaseUrl,
    OptionalBearerToken,
    OrderBy,
    ResourceId,
    WorkflowStatusFilter,
)
from nerm.tools._reference_catalog import execute_with_nerm_error_json, extract_list_records, resolve_connection
from pydantic import ValidationError


def _list_workflow_resource(
    path: str,
    limit: int = 100,
    offset: int = 0,
    force_all: bool = False,
    nerm_base_url: str | None = None,
    nerm_bearer_token: str | None = None,
    extra_params: dict[str, str | bool] | None = None,
) -> dict:
    try:
        bounded_limit, bounded_offset = normalize_pagination(limit=limit, offset=offset)
    except ValidationError as exc:
        return pagination_validation_error(exc)
    base_url, bearer_token = resolve_connection(nerm_base_url=nerm_base_url, nerm_bearer_token=nerm_bearer_token)
    client = NermHttpClient(base_url=base_url, bearer_token=bearer_token)
    def _fetch_page(page_offset: int, page_limit: int, _pages: int, _collected: int) -> object:
        params = {
            "limit": page_limit,
            "offset": page_offset,
            "metadata": True,
        }
        if extra_params:
            params.update(extra_params)
        return client.request("GET", path, timeout=15.0, params=params)

    def _parse_page(payload: object) -> list[dict]:
        if not isinstance(payload, dict):
            return []
        page_items = extract_list_records(payload, preferred_keys=("workflow_sessions",))
        return [normalize_workflow_session_item(item) for item in page_items]

    items, pages, pagination_limited, total_count, confirmation_needed = collect_paginated_items(
        bounded_limit=bounded_limit,
        bounded_offset=bounded_offset,
        force_all=force_all,
        fetch_page=_fetch_page,
        parse_page_items=_parse_page,
    )
    if confirmation_needed:
        return confirmation_needed

    response = {
        "items": items,
        "limit": bounded_limit,
        "offset": bounded_offset,
        "pages_fetched": pages,
        "pagination_limited": pagination_limited,
        "returned_count": len(items),
        "unique_item_count": unique_item_count(items),
    }
    if total_count is not None:
        response["total"] = total_count
    return response


def nerm_list_workflow_session_statuses(
    limit: Int32Positive = 100,
    offset: Int32NonNegative = 0,
    force_all: ForceAllFlag = False,
    order: OrderBy = None,
    profile_id: str | None = None,
    uid: str | None = None,
    workflow_id: str | None = None,
    requester_id: str | None = None,
    metadata: MetadataFlag = None,
    nerm_base_url: OptionalBaseUrl = None,
    nerm_bearer_token: OptionalBearerToken = None,
) -> dict:
    """List distinct workflow execution statuses from workflow sessions.

    Use for workflow/runtime state vocabulary, not profile business status.
    """
    def _run() -> dict:
        sessions = _list_workflow_resource(
            path=WORKFLOW_SESSIONS,
            limit=limit,
            offset=offset,
            force_all=force_all,
            extra_params={
                k: v
                for k, v in {
                    "order": order,
                    "profile_id": profile_id,
                    "uid": uid,
                    "workflow_id": workflow_id,
                    "requester_id": requester_id,
                    "metadata": metadata,
                }.items()
                if v is not None
            }
            or None,
            nerm_base_url=nerm_base_url,
            nerm_bearer_token=nerm_bearer_token,
        )
        if "error" in sessions:
            return sessions
        seen: set[str] = set()
        statuses: list[dict[str, str]] = []
        for item in sessions.get("items", []):
            if not isinstance(item, dict):
                continue
            status = str(item.get("status") or "").strip()
            if status and status not in seen:
                seen.add(status)
                statuses.append({"status": status})
        return {"items": statuses, "limit": sessions["limit"], "offset": sessions["offset"], "total": len(statuses)}

    return execute_with_nerm_error_json(_run)


def nerm_list_workflow_sessions(
    limit: Int32Positive = 100,
    offset: Int32NonNegative = 0,
    status: WorkflowStatusFilter = None,
    force_all: ForceAllFlag = False,
    order: OrderBy = None,
    profile_id: str | None = None,
    uid: str | None = None,
    workflow_id: str | None = None,
    requester_id: str | None = None,
    metadata: MetadataFlag = None,
    nerm_base_url: OptionalBaseUrl = None,
    nerm_bearer_token: OptionalBearerToken = None,
) -> dict:
    """List workflow session execution records.

    Use for submitted workflow state (pending approval, failed, completed), not assignment profiles.
    Do not use this for profile lifecycle/business status requests.
    """
    def _run() -> dict:
        extra_params: dict[str, str | bool] | None = {
            k: v
            for k, v in {
                "order": order,
                "profile_id": profile_id,
                "uid": uid,
                "workflow_id": workflow_id,
                "requester_id": requester_id,
                "metadata": metadata,
            }.items()
            if v is not None
        } or None
        if status:
            # status is already constrained by WorkflowStatusFilter (API-spec value set)
            extra_params = {**(extra_params or {}), "status": status}
        return _list_workflow_resource(
            path=WORKFLOW_SESSIONS,
            limit=limit,
            offset=offset,
            force_all=force_all,
            nerm_base_url=nerm_base_url,
            nerm_bearer_token=nerm_bearer_token,
            extra_params=extra_params,
        )

    return execute_with_nerm_error_json(_run)


def nerm_get_workflow_session(
    workflow_session_id: ResourceId,
    nerm_base_url: OptionalBaseUrl = None,
    nerm_bearer_token: OptionalBearerToken = None,
) -> dict:
    """Fetch a single workflow session by workflow session identifier."""
    def _run() -> dict:
        sessions = _list_workflow_resource(
            path=WORKFLOW_SESSIONS,
            limit=200,
            offset=0,
            force_all=True,
            nerm_base_url=nerm_base_url,
            nerm_bearer_token=nerm_bearer_token,
        )
        for item in sessions.get("items", []):
            if not isinstance(item, dict):
                continue
            if workflow_session_id in {
                str(item.get("id") or ""),
                str(item.get("workflow_session_id") or ""),
                str(item.get("workflow_session_full_id") or ""),
            }:
                return normalize_workflow_session_item(item)
        return {"error": "nerm_api_error", "status": 404, "body": f"workflow session {workflow_session_id} not found"}

    return execute_with_nerm_error_json(_run)


def _submit_workflow_action(
    payload: dict,
    workflow_id: str,
    nerm_base_url: str | None = None,
    nerm_bearer_token: str | None = None,
) -> dict:
    if not workflow_id:
        raise ValueError("workflow_id is required. Set payload.workflow_id or NERM_ADD_*_WORKFLOW_ID.")
    base_url, bearer_token = resolve_connection(nerm_base_url=nerm_base_url, nerm_bearer_token=nerm_bearer_token)
    client = NermHttpClient(base_url=base_url, bearer_token=bearer_token)
    # Spec-aligned workflow submission endpoint.
    request_body = payload.copy()
    request_body.setdefault("workflow_id", workflow_id)
    result = client.request("POST", WORKFLOW_SESSIONS, timeout=30.0, json=request_body)
    session_id = (
        result.get("workflow_session_full_id")
        or result.get("workflow_session_id")
        or result.get("id")
        or payload.get("workflow_session_full_id")
        or ""
    )
    status = str(result.get("status") or "Pending")
    return format_workflow_submission(workflow_session_full_id=session_id, status=status)


def nerm_add_location_via_workflow(
    payload: dict,
    nerm_base_url: str | None = None,
    nerm_bearer_token: str | None = None,
) -> dict:
    """Submit workflow request to add a location.

    Returns request-submitted status metadata, not a direct profile update confirmation.
    """
    settings = get_settings()
    workflow_id = payload.get("workflow_id") or settings.nerm_add_location_workflow_id
    return execute_with_nerm_error_json(
        lambda: _submit_workflow_action(
            payload=payload,
            workflow_id=workflow_id,
            nerm_base_url=nerm_base_url,
            nerm_bearer_token=nerm_bearer_token,
        )
    )


def nerm_add_department_via_workflow(
    payload: dict,
    nerm_base_url: str | None = None,
    nerm_bearer_token: str | None = None,
) -> dict:
    """Submit workflow request to add a department.

    Returns request-submitted status metadata, not a direct profile update confirmation.
    """
    settings = get_settings()
    workflow_id = payload.get("workflow_id") or settings.nerm_add_department_workflow_id
    return execute_with_nerm_error_json(
        lambda: _submit_workflow_action(
            payload=payload,
            workflow_id=workflow_id,
            nerm_base_url=nerm_base_url,
            nerm_bearer_token=nerm_bearer_token,
        )
    )


def nerm_add_organization_via_workflow(
    payload: dict,
    nerm_base_url: str | None = None,
    nerm_bearer_token: str | None = None,
) -> dict:
    """Submit workflow request to add an organization.

    Returns request-submitted status metadata, not a direct profile update confirmation.
    """
    settings = get_settings()
    workflow_id = payload.get("workflow_id") or settings.nerm_add_organization_workflow_id
    return execute_with_nerm_error_json(
        lambda: _submit_workflow_action(
            payload=payload,
            workflow_id=workflow_id,
            nerm_base_url=nerm_base_url,
            nerm_bearer_token=nerm_bearer_token,
        )
    )


def nerm_get_job_status(
    job_id: ResourceId,
    nerm_base_url: OptionalBaseUrl = None,
    nerm_bearer_token: OptionalBearerToken = None,
) -> dict:
    """Fetch asynchronous job status by job identifier."""
    def _run() -> dict:
        base_url, bearer_token = resolve_connection(nerm_base_url=nerm_base_url, nerm_bearer_token=nerm_bearer_token)
        client = NermHttpClient(base_url=base_url, bearer_token=bearer_token)
        params: dict[str, str | int | bool] = {"job_id": job_id}
        payload = client.request("GET", JOB_STATUS, timeout=15.0, params=params)
        if isinstance(payload, dict):
            payload.setdefault("requested_job_id", job_id)
            return normalize_job_status_payload(payload)
        return payload

    return execute_with_nerm_error_json(_run)
