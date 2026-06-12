from datetime import datetime, timedelta, timezone

from nerm.client.endpoints import DELEGATIONS, USERS
from nerm.client.http_client import NermHttpClient
from nerm.schemas.delegations import DelegationUpdatePayload, DelegationWritePayload, normalize_delegation_item
from nerm.schemas.common import normalize_pagination, pagination_validation_error
from nerm.services.pagination import (
    collect_paginated_items,
    unique_item_count,
)
from nerm.errors import NermApiError
from nerm.tools.param_specs import (
    ForceAllFlag,
    Int32NonNegative,
    Int32Positive,
    MetadataFlag,
    OptionalBaseUrl,
    OptionalBearerToken,
    ResourceId,
)
from nerm.tools._reference_catalog import execute_with_nerm_error_json, extract_list_records, resolve_connection
from pydantic import ValidationError


def _normalize_delegation_payload(payload: dict) -> dict:
    delegation = payload.get("delegation")
    raw = delegation if isinstance(delegation, dict) else payload
    validated = DelegationWritePayload.model_validate(raw)
    return validated.to_api_payload()


def _normalize_delegation_update_payload(payload: dict) -> dict:
    delegation = payload.get("delegation")
    raw = delegation if isinstance(delegation, dict) else payload
    validated = DelegationUpdatePayload.model_validate(raw)
    return validated.to_api_payload()


def _fetch_user_lookup(client: NermHttpClient, user_ids: set[str]) -> dict[str, dict]:
    users_by_id: dict[str, dict] = {}
    for user_id in sorted(user_ids):
        if not user_id:
            continue
        try:
            payload = client.request("GET", f"{USERS}/{user_id}", timeout=15.0)
        except NermApiError:
            continue
        if isinstance(payload, dict):
            users_by_id[user_id] = payload
    return users_by_id


def _extract_user_identity(payload: dict) -> dict:
    """Normalize likely /users response shapes into identity fields."""
    if isinstance(payload.get("user"), dict):
        raw = payload["user"]
    elif isinstance(payload.get("users"), list) and payload["users"] and isinstance(payload["users"][0], dict):
        raw = payload["users"][0]
    else:
        raw = payload
    return raw if isinstance(raw, dict) else {}


def _enrich_delegations_with_user_details(items: list[dict], users_by_id: dict[str, dict]) -> list[dict]:
    enriched: list[dict] = []
    for item in items:
        row = dict(item)
        delegator_id = str(row.get("delegator_id") or "")
        delegate_id = str(row.get("delegate_id") or "")
        delegator = _extract_user_identity(users_by_id.get(delegator_id, {}))
        delegate = _extract_user_identity(users_by_id.get(delegate_id, {}))
        row["delegator_name"] = delegator.get("name") or delegator.get("full_name") or delegator.get("display_name")
        row["delegator_login"] = delegator.get("login") or delegator.get("uid") or delegator.get("username")
        row["delegator_email"] = delegator.get("email") or delegator.get("mail")
        row["delegate_name"] = delegate.get("name") or delegate.get("full_name") or delegate.get("display_name")
        row["delegate_login"] = delegate.get("login") or delegate.get("uid") or delegate.get("username")
        row["delegate_email"] = delegate.get("email") or delegate.get("mail")
        enriched.append(row)
    return enriched


def _normalize_delegation_response(result: object) -> dict | object:
    if not isinstance(result, dict):
        return result
    delegation_payload = result.get("delegation")
    if isinstance(delegation_payload, dict):
        return {"delegation": normalize_delegation_item(delegation_payload)}
    return {"delegation": normalize_delegation_item(result)}


def _map_expiration_error(exc: NermApiError) -> dict | None:
    if exc.status != 400:
        return None
    body = str(exc.body)
    if "Expiration must be after today" not in body:
        return None
    return {
        "error": "invalid_delegation_spec",
        "message": "Delegation expiration must be after today.",
        "guidance": {
            "preferred_input": "expiration",
            "examples": [
                {"expiration": "2026-07-05T00:00:00Z"},
            ],
            "required_key": "expiration",
            "note": "Use the exact key 'expiration'. If user asks for a relative period, compute one absolute ISO-8601 date/time first.",
        },
        "details": body,
    }


def _map_delegation_validation_error(exc: ValidationError) -> dict | None:
    details = exc.errors(include_url=False)
    unsupported_expiration_keys: list[str] = []
    for err in details:
        if err.get("type") != "extra_forbidden":
            continue
        loc = err.get("loc")
        if not isinstance(loc, (list, tuple)) or not loc:
            continue
        key = str(loc[-1])
        if key in {"expiration_date", "expires_at", "end_date"}:
            unsupported_expiration_keys.append(key)
    if not unsupported_expiration_keys:
        return None
    now_utc = datetime.now(timezone.utc)
    return {
        "error": "invalid_delegation_spec",
        "message": "Use expiration key only for delegation end time.",
        "guidance": {
            "required_key": "expiration",
            "unsupported_keys": sorted(set(unsupported_expiration_keys)),
            "current_time_utc": now_utc.isoformat().replace("+00:00", "Z"),
            "example_30_days_utc": (now_utc + timedelta(days=30)).isoformat().replace("+00:00", "Z"),
            "example_payload": {
                "payload": {
                    "delegator_id": "<delegator_user_uuid>",
                    "delegate_id": "<delegate_user_uuid>",
                    "expiration": (now_utc + timedelta(days=30)).isoformat().replace("+00:00", "Z"),
                }
            },
        },
        "details": details,
    }


def _validate_future_expiration(payload: dict) -> dict | None:
    expiration_raw = payload.get("expiration")
    if not isinstance(expiration_raw, str) or not expiration_raw.strip():
        return None
    try:
        expiration_dt = datetime.fromisoformat(expiration_raw.replace("Z", "+00:00"))
    except ValueError:
        return {
            "error": "invalid_delegation_spec",
            "message": "Delegation expiration must be a valid ISO-8601 date-time string.",
            "guidance": {
                "preferred_input": "expiration",
                "examples": [
                    {"expiration": "2026-07-05T00:00:00Z"},
                ],
                    "required_key": "expiration",
            },
        }
    if expiration_dt.tzinfo is None:
        expiration_dt = expiration_dt.replace(tzinfo=timezone.utc)
    now_utc = datetime.now(timezone.utc)
    if expiration_dt > now_utc:
        return None
    return {
        "error": "invalid_delegation_spec",
        "message": "Delegation expiration must be after today.",
        "guidance": {
            "preferred_input": "expiration",
            "current_time_utc": now_utc.isoformat().replace("+00:00", "Z"),
            "example_30_days_utc": (now_utc + timedelta(days=30)).isoformat().replace("+00:00", "Z"),
            "note": "Use a future ISO-8601 expiration. For 'ends in 30 days', set expiration to now + 30 days once.",
        },
    }


def nerm_list_delegations(
    limit: Int32Positive = 100,
    offset: Int32NonNegative = 0,
    force_all: ForceAllFlag = False,
    delegate_id: str | None = None,
    delegator_id: str | None = None,
    expired: bool | None = None,
    include_user_details: bool = True,
    metadata: MetadataFlag = None,
    nerm_base_url: OptionalBaseUrl = None,
    nerm_bearer_token: OptionalBearerToken = None,
) -> dict:
    """List user delegation relationships (delegator/delegate coverage).

    Use for delegated authority questions. Do not use for assignment/profile analytics.
    For assignment or organization business state, use profile type resolution and
    nerm_run_advanced_search instead.
    """
    def _run() -> dict:
        try:
            bounded_limit, bounded_offset = normalize_pagination(limit=limit, offset=offset)
        except ValidationError as exc:
            return pagination_validation_error(exc)
        base_url, bearer_token = resolve_connection(nerm_base_url=nerm_base_url, nerm_bearer_token=nerm_bearer_token)
        client = NermHttpClient(base_url=base_url, bearer_token=bearer_token)
        def _fetch_page(page_offset: int, page_limit: int, _pages: int, _collected: int) -> object:
            params: dict[str, str | int | bool] = {
                "limit": page_limit,
                "offset": page_offset,
                "metadata": True,
            }
            if delegate_id:
                params["delegate_id"] = delegate_id
            if delegator_id:
                params["delegator_id"] = delegator_id
            if expired is not None:
                params["expired"] = expired
            return client.request("GET", DELEGATIONS, timeout=30.0, params=params)

        def _parse_page(payload: object) -> list[dict]:
            if not isinstance(payload, dict):
                return []
            page_items = extract_list_records(payload, preferred_keys=("delegations",))
            return [normalize_delegation_item(item) for item in page_items]

        items, pages, pagination_limited, total_count, confirmation_needed = collect_paginated_items(
            bounded_limit=bounded_limit,
            bounded_offset=bounded_offset,
            force_all=force_all,
            fetch_page=_fetch_page,
            parse_page_items=_parse_page,
        )
        if confirmation_needed:
            return confirmation_needed

        if include_user_details:
            user_ids = {
                str(item.get("delegator_id") or "")
                for item in items
                if isinstance(item, dict)
            } | {
                str(item.get("delegate_id") or "")
                for item in items
                if isinstance(item, dict)
            }
            users_by_id = _fetch_user_lookup(client, user_ids)
            items = _enrich_delegations_with_user_details(items, users_by_id)

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

    return execute_with_nerm_error_json(_run)


def nerm_get_delegation(
    delegation_id: ResourceId,
    nerm_base_url: OptionalBaseUrl = None,
    nerm_bearer_token: OptionalBearerToken = None,
) -> dict:
    """Fetch one delegation relationship by delegation ID."""
    def _run() -> dict:
        base_url, bearer_token = resolve_connection(nerm_base_url=nerm_base_url, nerm_bearer_token=nerm_bearer_token)
        client = NermHttpClient(base_url=base_url, bearer_token=bearer_token)
        payload = client.request("GET", f"{DELEGATIONS}/{delegation_id}", timeout=15.0)
        return normalize_delegation_item(payload) if isinstance(payload, dict) else payload

    return execute_with_nerm_error_json(_run)


def nerm_create_delegation(
    payload: dict,
    nerm_base_url: str | None = None,
    nerm_bearer_token: str | None = None,
) -> dict:
    """Create a delegation record between two lifecycle users.

    Use exact key `expiration` with ISO-8601 date-time. For relative end-date requests,
    compute one absolute future expiration and submit a single create request.
    """
    def _run() -> dict:
        base_url, bearer_token = resolve_connection(nerm_base_url=nerm_base_url, nerm_bearer_token=nerm_bearer_token)
        client = NermHttpClient(base_url=base_url, bearer_token=bearer_token)
        try:
            delegation = _normalize_delegation_payload(payload)
        except ValidationError as exc:
            mapped = _map_delegation_validation_error(exc)
            if mapped:
                return mapped
            return {
                "error": "invalid_delegation_spec",
                "message": "delegation payload failed schema validation.",
                "details": exc.errors(include_url=False),
            }
        expiration_validation = _validate_future_expiration(delegation)
        if expiration_validation is not None:
            return expiration_validation
        body = {"delegation": delegation}
        try:
            result = client.request("POST", DELEGATIONS, timeout=30.0, json=body)
        except NermApiError as exc:
            mapped = _map_expiration_error(exc)
            if mapped:
                return mapped
            raise
        return _normalize_delegation_response(result)

    return execute_with_nerm_error_json(_run)


def nerm_update_delegation(
    delegation_id: str,
    payload: dict,
    nerm_base_url: str | None = None,
    nerm_bearer_token: str | None = None,
) -> dict:
    """Update an existing delegation record.

    Use exact key `expiration` with ISO-8601 date-time when changing end time.
    Do not use `end_date`, `expiration_date`, or `expires_at`.
    """
    def _run() -> dict:
        base_url, bearer_token = resolve_connection(nerm_base_url=nerm_base_url, nerm_bearer_token=nerm_bearer_token)
        client = NermHttpClient(base_url=base_url, bearer_token=bearer_token)
        try:
            delegation = _normalize_delegation_update_payload(payload)
        except ValidationError as exc:
            mapped = _map_delegation_validation_error(exc)
            if mapped:
                return mapped
            return {
                "error": "invalid_delegation_spec",
                "message": "delegation payload failed schema validation.",
                "details": exc.errors(include_url=False),
            }
        if not delegation:
            return {
                "error": "invalid_delegation_spec",
                "message": "delegation payload must include at least one updatable field.",
            }
        expiration_validation = _validate_future_expiration(delegation)
        if expiration_validation is not None:
            return expiration_validation
        body = {"delegation": delegation}
        try:
            result = client.request("PATCH", f"{DELEGATIONS}/{delegation_id}", timeout=30.0, json=body)
        except NermApiError as exc:
            mapped = _map_expiration_error(exc)
            if mapped:
                return mapped
            raise
        return _normalize_delegation_response(result)

    return execute_with_nerm_error_json(_run)


def nerm_delete_delegation(
    delegation_id: str,
    nerm_base_url: str | None = None,
    nerm_bearer_token: str | None = None,
) -> dict:
    """Delete a delegation relationship by delegation ID."""
    def _run() -> dict:
        base_url, bearer_token = resolve_connection(nerm_base_url=nerm_base_url, nerm_bearer_token=nerm_bearer_token)
        client = NermHttpClient(base_url=base_url, bearer_token=bearer_token)
        result = client.request("DELETE", f"{DELEGATIONS}/{delegation_id}", timeout=30.0)
        return result if isinstance(result, dict) else {"message": str(result or "")}

    return execute_with_nerm_error_json(_run)
