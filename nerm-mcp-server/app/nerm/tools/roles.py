import json as pyjson

from nerm.client.endpoints import ROLE_PROFILES, ROLES
from nerm.client.http_client import NermHttpClient
from nerm.errors import NermApiError
from nerm.schemas.common import normalize_pagination, pagination_validation_error
from nerm.schemas.roles import normalize_role_item
from nerm.services.pagination import collect_paginated_items, unique_item_count
from nerm.tools.param_specs import (
    ForceAllFlag,
    Int32NonNegative,
    Int32Positive,
    MetadataFlag,
    OptionalBaseUrl,
    OptionalBearerToken,
    OrderBy,
    RoleType,
    ResourceId,
)
from nerm.tools._reference_catalog import execute_with_nerm_error_json, extract_list_records, resolve_connection
from pydantic import ValidationError


def _list_resource(
    path: str,
    preferred_list_key: str,
    limit: int = 100,
    offset: int = 0,
    force_all: bool = False,
    query: dict[str, str | int | bool] | None = None,
    nerm_base_url: str | None = None,
    nerm_bearer_token: str | None = None,
) -> dict:
    def _is_no_roles_found_error(exc: NermApiError) -> bool:
        if exc.status not in {400, 404}:
            return False
        body = str(exc.body or "")
        if "no roles found" in body.lower():
            return True
        try:
            parsed = pyjson.loads(body)
        except Exception:  # noqa: BLE001
            return False
        if isinstance(parsed, dict):
            return "no roles found" in str(parsed.get("error", "")).lower()
        return False

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
        if query:
            params.update(query)
        try:
            return client.request("GET", path, timeout=15.0, params=params)
        except NermApiError as exc:
            if _is_no_roles_found_error(exc):
                return {preferred_list_key: []}
            raise

    def _parse_page(payload: object) -> list[dict]:
        if not isinstance(payload, dict):
            return []
        page_items = extract_list_records(payload, preferred_keys=(preferred_list_key,))
        return [normalize_role_item(item) for item in page_items]

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


def _get_resource(
    path: str,
    resource_id: str,
    nerm_base_url: str | None = None,
    nerm_bearer_token: str | None = None,
) -> dict:
    base_url, bearer_token = resolve_connection(nerm_base_url=nerm_base_url, nerm_bearer_token=nerm_bearer_token)
    client = NermHttpClient(base_url=base_url, bearer_token=bearer_token)
    payload = client.request("GET", f"{path}/{resource_id}", timeout=15.0)
    return normalize_role_item(payload) if isinstance(payload, dict) else payload


def nerm_list_roles(
    limit: Int32Positive = 100,
    offset: Int32NonNegative = 0,
    force_all: ForceAllFlag = False,
    order: OrderBy = None,
    metadata: MetadataFlag = None,
    type: RoleType | None = None,  # noqa: A002
    nerm_base_url: OptionalBaseUrl = None,
    nerm_bearer_token: OptionalBearerToken = None,
) -> dict:
    """List role catalog records.

    Use for role/access taxonomy lookups, not assignment engagement analytics.
    This tool does not support name filtering from API spec.
    Role type glossary: Portal/Collaboration role == `NeaccessRole`;
    Lifecycle role == `NeprofileRole`.
    """
    merged_query: dict[str, str | int | bool] = {}
    if order:
        merged_query["order"] = order
    if metadata is not None:
        merged_query["metadata"] = metadata
    if type:
        merged_query["type"] = type
    return execute_with_nerm_error_json(
        lambda: _list_resource(
            path=ROLES,
            preferred_list_key="roles",
            limit=limit,
            offset=offset,
            force_all=force_all,
            query=merged_query or None,
            nerm_base_url=nerm_base_url,
            nerm_bearer_token=nerm_bearer_token,
        )
    )


def nerm_get_role(
    role_id: ResourceId,
    nerm_base_url: OptionalBaseUrl = None,
    nerm_bearer_token: OptionalBearerToken = None,
) -> dict:
    """Fetch one role record by role ID."""
    return execute_with_nerm_error_json(
        lambda: _get_resource(
            path=ROLES,
            resource_id=role_id,
            nerm_base_url=nerm_base_url,
            nerm_bearer_token=nerm_bearer_token,
        )
    )


def nerm_list_role_profiles(
    limit: Int32Positive = 100,
    offset: Int32NonNegative = 0,
    force_all: ForceAllFlag = False,
    order: OrderBy = None,
    role_id: str | None = None,
    profile_id: str | None = None,
    metadata: MetadataFlag = None,
    nerm_base_url: OptionalBaseUrl = None,
    nerm_bearer_token: OptionalBearerToken = None,
) -> dict:
    """List role-to-profile relationship mappings."""
    merged_query: dict[str, str | int | bool] = {}
    if order:
        merged_query["order"] = order
    if role_id:
        merged_query["role_id"] = role_id
    if profile_id:
        merged_query["profile_id"] = profile_id
    if metadata is not None:
        merged_query["metadata"] = metadata
    return execute_with_nerm_error_json(
        lambda: _list_resource(
            path=ROLE_PROFILES,
            preferred_list_key="role_profiles",
            limit=limit,
            offset=offset,
            force_all=force_all,
            query=merged_query or None,
            nerm_base_url=nerm_base_url,
            nerm_bearer_token=nerm_bearer_token,
        )
    )


def nerm_get_role_profile(
    role_profile_id: ResourceId,
    nerm_base_url: OptionalBaseUrl = None,
    nerm_bearer_token: OptionalBearerToken = None,
) -> dict:
    """Fetch one role-profile relationship by ID."""
    return execute_with_nerm_error_json(
        lambda: _get_resource(
            path=ROLE_PROFILES,
            resource_id=role_profile_id,
            nerm_base_url=nerm_base_url,
            nerm_bearer_token=nerm_bearer_token,
        )
    )
