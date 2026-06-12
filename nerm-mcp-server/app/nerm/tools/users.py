import json as pyjson
import os

import jwt

from nerm.client.endpoints import ROLES, USER_MANAGERS, USER_PROFILES, USER_ROLES, USERS
from nerm.client.http_client import NermHttpClient
from nerm.errors import NermApiError
from nerm.schemas.roles import normalize_role_item
from nerm.schemas.common import normalize_pagination, pagination_validation_error
from nerm.schemas.users import normalize_user_item
from nerm.services.pagination import (
    collect_paginated_items,
    unique_item_count,
)
from nerm.tools.param_specs import (
    ForceAllFlag,
    Int32NonNegative,
    Int32Positive,
    MetadataFlag,
    OptionalBaseUrl,
    OptionalBearerToken,
    OrderBy,
    RelationshipType,
    ResourceId,
    UserStatus,
    UserType,
)
from nerm.tools._reference_catalog import execute_with_nerm_error_json, extract_list_records, resolve_connection
from nerm.tools.roles import _get_resource, _list_resource
from pydantic import ValidationError


def _is_no_users_found_error(exc: NermApiError) -> bool:
    if exc.status not in {400, 404}:
        return False
    body = str(exc.body or "")
    if "no users found" in body.lower():
        return True
    try:
        parsed = pyjson.loads(body)
    except Exception:  # noqa: BLE001
        return False
    if isinstance(parsed, dict):
        return "no users found" in str(parsed.get("error", "")).lower()
    return False


def _normalize_login_candidate(value: str) -> str:
    text = value.strip().replace("@", " ").replace("_", " ").replace("-", " ")
    parts = [token for token in text.replace(".", " ").split() if token]
    if not parts:
        return value.strip()
    return ".".join(parts).lower()


def _fallback_user_filters(name: str | None, login: str | None, email: str | None) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    def add_filter(key: str, value: str | None) -> None:
        if not value:
            return
        pair = (key, value)
        if pair in seen:
            return
        seen.add(pair)
        candidates.append({key: value})

    if name and not login:
        login_candidate = _normalize_login_candidate(name)
        add_filter("login", login_candidate)
        add_filter("name", name.strip().title())
    if email and "@" not in email and not login:
        add_filter("login", _normalize_login_candidate(email))
    return candidates


def nerm_list_users(
    limit: Int32Positive = 100,
    offset: Int32NonNegative = 0,
    force_all: ForceAllFlag = False,
    order: OrderBy = None,
    name: str | None = None,
    login: str | None = None,
    title: str | None = None,
    user_status: UserStatus | None = None,
    type: UserType | None = None,  # noqa: A002
    email: str | None = None,
    metadata: MetadataFlag = None,
    sailpoint_identity_id: str | None = None,
    nerm_base_url: OptionalBaseUrl = None,
    nerm_bearer_token: OptionalBearerToken = None,
) -> dict:
    """List lifecycle/access users for identity resolution and relationship filters.

    Type glossary reminder: Portal user == `NeaccessUser`; Lifecycle user ==
    `NeprofileUser`; "Collaboration" refers to portal context.
    Use to resolve names/emails to user IDs (owners, contributors, delegators, delegates).
    If a name/email search returns "no users found", this tool automatically retries
    safe login-normalized fallbacks on the first page.
    """
    def _run() -> dict:
        try:
            bounded_limit, bounded_offset = normalize_pagination(limit=limit, offset=offset)
        except ValidationError as exc:
            return pagination_validation_error(exc)
        base_url, bearer_token = resolve_connection(nerm_base_url=nerm_base_url, nerm_bearer_token=nerm_bearer_token)
        client = NermHttpClient(base_url=base_url, bearer_token=bearer_token)
        static_params: dict[str, str | bool] = {}
        if order:
            static_params["order"] = order
        if name:
            static_params["name"] = name
        if login:
            static_params["login"] = login
        if title:
            static_params["title"] = title
        if user_status:
            static_params["user_status"] = user_status
        if type:
            static_params["type"] = type
        if email:
            static_params["email"] = email
        if metadata is not None:
            static_params["metadata"] = metadata
        if sailpoint_identity_id:
            static_params["sailpoint_identity_id"] = sailpoint_identity_id
        active_filter = dict(static_params)
        fallback_filters = _fallback_user_filters(name=name, login=login, email=email)

        def _fetch_page(page_offset: int, page_limit: int, pages_fetched: int, collected_count: int) -> object:
            nonlocal active_filter
            params: dict[str, str | int | bool] = {
                "limit": page_limit,
                "offset": page_offset,
                "metadata": True,
            }
            params.update(active_filter)
            try:
                return client.request("GET", USERS, timeout=15.0, params=params)
            except NermApiError as exc:
                if not _is_no_users_found_error(exc):
                    raise
                if not (pages_fetched == 0 and page_offset == bounded_offset and collected_count == 0):
                    return {"users": []}
                fallback_payload: object | None = None
                for fallback in fallback_filters:
                    fallback_params = {"limit": params["limit"], "offset": params["offset"], **fallback}
                    try:
                        fallback_payload = client.request("GET", USERS, timeout=15.0, params=fallback_params)
                        active_filter = dict(fallback)
                        break
                    except NermApiError as fallback_exc:
                        if _is_no_users_found_error(fallback_exc):
                            continue
                        raise
                if fallback_payload is None:
                    return {"users": []}
                return fallback_payload

        def _parse_page(payload: object) -> list[dict]:
            if not isinstance(payload, dict):
                return []
            page_items = extract_list_records(payload, preferred_keys=("users",))
            return [normalize_user_item(item) for item in page_items]

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

    return execute_with_nerm_error_json(_run)


def nerm_get_user(
    user_id: ResourceId,
    nerm_base_url: OptionalBaseUrl = None,
    nerm_bearer_token: OptionalBearerToken = None,
) -> dict:
    """Fetch one user record by user ID."""
    def _run() -> dict:
        base_url, bearer_token = resolve_connection(nerm_base_url=nerm_base_url, nerm_bearer_token=nerm_bearer_token)
        client = NermHttpClient(base_url=base_url, bearer_token=bearer_token)
        payload = client.request("GET", f"{USERS}/{user_id}", timeout=15.0)
        return normalize_user_item(payload) if isinstance(payload, dict) else payload

    return execute_with_nerm_error_json(_run)


def _extract_user_identity(payload: dict) -> dict:
    if isinstance(payload.get("user"), dict):
        raw = payload["user"]
    elif isinstance(payload.get("users"), list) and payload["users"] and isinstance(payload["users"][0], dict):
        raw = payload["users"][0]
    else:
        raw = payload
    return normalize_user_item(raw) if isinstance(raw, dict) else {}


def _extract_role_identity(payload: dict) -> dict:
    if isinstance(payload.get("role"), dict):
        raw = payload["role"]
    elif isinstance(payload.get("roles"), list) and payload["roles"] and isinstance(payload["roles"][0], dict):
        raw = payload["roles"][0]
    else:
        raw = payload
    return normalize_role_item(raw) if isinstance(raw, dict) else {}


def _enrich_user_roles_with_details(
    client: NermHttpClient,
    items: list[dict],
    *,
    include_user_details: bool,
    include_role_details: bool,
) -> list[dict]:
    user_ids = {
        str(item.get("user_id") or "")
        for item in items
        if isinstance(item, dict) and item.get("user_id")
    }
    role_ids = {
        str(item.get("role_id") or "")
        for item in items
        if isinstance(item, dict) and item.get("role_id")
    }
    users_by_id: dict[str, dict] = {}
    roles_by_id: dict[str, dict] = {}
    if include_user_details:
        for user_id in sorted(user_ids):
            try:
                payload = client.request("GET", f"{USERS}/{user_id}", timeout=15.0)
            except Exception:  # noqa: BLE001
                continue
            if isinstance(payload, dict):
                users_by_id[user_id] = _extract_user_identity(payload)
    if include_role_details:
        for role_id in sorted(role_ids):
            try:
                payload = client.request("GET", f"{ROLES}/{role_id}", timeout=15.0)
            except Exception:  # noqa: BLE001
                continue
            if isinstance(payload, dict):
                roles_by_id[role_id] = _extract_role_identity(payload)

    enriched: list[dict] = []
    for item in items:
        row = dict(item)
        if include_user_details:
            user = users_by_id.get(str(row.get("user_id") or ""), {})
            row["user_name"] = user.get("name")
            row["user_login"] = user.get("login") or user.get("uid") or user.get("username")
            row["user_email"] = user.get("email") or user.get("mail")
            row["user_status"] = user.get("status")
            row["user_type"] = user.get("type")
        if include_role_details:
            role = roles_by_id.get(str(row.get("role_id") or ""), {})
            row["role_name"] = role.get("name")
            row["role_uid"] = role.get("uid")
            row["role_private"] = role.get("private_role")
            row["role_groups"] = role.get("groups")
        enriched.append(row)
    return enriched


def nerm_list_user_roles(
    limit: Int32Positive = 100,
    offset: Int32NonNegative = 0,
    force_all: ForceAllFlag = False,
    order: OrderBy = None,
    user_id: str | None = None,
    role_id: str | None = None,
    include_user_details: bool = True,
    include_role_details: bool = True,
    metadata: MetadataFlag = None,
    nerm_base_url: OptionalBaseUrl = None,
    nerm_bearer_token: OptionalBearerToken = None,
) -> dict:
    """List user-to-role relationship records.

    Use for access relationships; do not use for assignment profile state.
    Type glossary reminder: Portal user == `NeaccessUser`, Lifecycle user ==
    `NeprofileUser`; Portal/Collaboration role == `NeaccessRole`, Lifecycle role ==
    `NeprofileRole`.
    By default, enriches each row with user_name/login/email/status/type and
    role_name/uid/private/groups using internal user and role lookups.
    """
    merged_query: dict[str, str | int | bool] = {}
    if order:
        merged_query["order"] = order
    if user_id:
        merged_query["user_id"] = user_id
    if role_id:
        merged_query["role_id"] = role_id
    if metadata is not None:
        merged_query["metadata"] = metadata

    def _run() -> dict:
        result = _list_resource(
            path=USER_ROLES,
            preferred_list_key="user_roles",
            limit=limit,
            offset=offset,
            force_all=force_all,
            query=merged_query or None,
            nerm_base_url=nerm_base_url,
            nerm_bearer_token=nerm_bearer_token,
        )
        if "error" in result or (not include_user_details and not include_role_details):
            return result
        items = result.get("items")
        if not isinstance(items, list) or not items:
            return result
        base_url, bearer_token = resolve_connection(nerm_base_url=nerm_base_url, nerm_bearer_token=nerm_bearer_token)
        client = NermHttpClient(base_url=base_url, bearer_token=bearer_token)
        result["items"] = _enrich_user_roles_with_details(
            client,
            [item for item in items if isinstance(item, dict)],
            include_user_details=include_user_details,
            include_role_details=include_role_details,
        )
        return result

    return execute_with_nerm_error_json(_run)


def nerm_get_user_role(
    user_role_id: ResourceId,
    nerm_base_url: OptionalBaseUrl = None,
    nerm_bearer_token: OptionalBearerToken = None,
) -> dict:
    """Fetch one user-role relationship by ID."""
    return execute_with_nerm_error_json(
        lambda: _get_resource(
            path=USER_ROLES,
            resource_id=user_role_id,
            nerm_base_url=nerm_base_url,
            nerm_bearer_token=nerm_bearer_token,
        )
    )


def nerm_list_user_managers(
    limit: Int32Positive = 100,
    offset: Int32NonNegative = 0,
    force_all: ForceAllFlag = False,
    order: OrderBy = None,
    user_id: str | None = None,
    manager_id: str | None = None,
    metadata: MetadataFlag = None,
    nerm_base_url: OptionalBaseUrl = None,
    nerm_bearer_token: OptionalBearerToken = None,
) -> dict:
    """List user-manager relationship records."""
    merged_query: dict[str, str | int | bool] = {}
    if order:
        merged_query["order"] = order
    if user_id:
        merged_query["user_id"] = user_id
    if manager_id:
        merged_query["manager_id"] = manager_id
    if metadata is not None:
        merged_query["metadata"] = metadata
    return execute_with_nerm_error_json(
        lambda: _list_resource(
            path=USER_MANAGERS,
            preferred_list_key="user_managers",
            limit=limit,
            offset=offset,
            force_all=force_all,
            query=merged_query or None,
            nerm_base_url=nerm_base_url,
            nerm_bearer_token=nerm_bearer_token,
        )
    )


def nerm_get_user_manager(
    manager_id: ResourceId,
    nerm_base_url: OptionalBaseUrl = None,
    nerm_bearer_token: OptionalBearerToken = None,
) -> dict:
    """Fetch one user-manager relationship by ID."""
    return execute_with_nerm_error_json(
        lambda: _get_resource(
            path=USER_MANAGERS,
            resource_id=manager_id,
            nerm_base_url=nerm_base_url,
            nerm_bearer_token=nerm_bearer_token,
        )
    )


def nerm_list_user_profiles(
    limit: Int32Positive = 100,
    offset: Int32NonNegative = 0,
    force_all: ForceAllFlag = False,
    order: OrderBy = None,
    user_id: str | None = None,
    ne_attribute_id: str | None = None,
    profile_id: str | None = None,
    relationship_type: RelationshipType | None = None,
    metadata: MetadataFlag = None,
    nerm_base_url: OptionalBaseUrl = None,
    nerm_bearer_token: OptionalBearerToken = None,
) -> dict:
    """List user-to-profile relationship mappings (owner/contributor style links).

    Use this tool to answer questions like:
    - "Which profiles is this user linked to?"
    - "Who are the owners/contributors for this profile?"
    - "Show user/profile links for a specific relationship attribute."

    Parameter guidance:
    - `user_id`: filter links for one user UUID.
    - `profile_id`: filter links for one profile UUID.
    - `ne_attribute_id`: constrain results to one relationship attribute UUID
      (helpful when multiple owner/contributor-style attributes exist).
    - `relationship_type`: constrain to API-supported relationship semantics
      (for example owner vs contributor style relationships).
    - Combine `user_id` + `profile_id` when checking whether a specific link exists.
    - `order` and `metadata` are pass-through query options for API sorting/metadata behavior.
    - `limit`/`offset` control pagination; use `force_all=True` only when the user explicitly asks
      for complete retrieval across pages.
    """
    merged_query: dict[str, str | int | bool] = {}
    if order:
        merged_query["order"] = order
    if user_id:
        merged_query["user_id"] = user_id
    if ne_attribute_id:
        merged_query["ne_attribute_id"] = ne_attribute_id
    if profile_id:
        merged_query["profile_id"] = profile_id
    if relationship_type:
        merged_query["relationship_type"] = relationship_type
    if metadata is not None:
        merged_query["metadata"] = metadata
    return execute_with_nerm_error_json(
        lambda: _list_resource(
            path=USER_PROFILES,
            preferred_list_key="user_profiles",
            limit=limit,
            offset=offset,
            force_all=force_all,
            query=merged_query or None,
            nerm_base_url=nerm_base_url,
            nerm_bearer_token=nerm_bearer_token,
        )
    )


def nerm_get_user_profile(
    user_profile_id: ResourceId,
    nerm_base_url: OptionalBaseUrl = None,
    nerm_bearer_token: OptionalBearerToken = None,
) -> dict:
    """Fetch one user-profile relationship by ID."""
    return execute_with_nerm_error_json(
        lambda: _get_resource(
            path=USER_PROFILES,
            resource_id=user_profile_id,
            nerm_base_url=nerm_base_url,
            nerm_bearer_token=nerm_bearer_token,
        )
    )


def nerm_examine_jwt_user() -> dict:
    """Decode JWT claims from NERM_INVOKE_AUTHORIZATION for local troubleshooting.

    This is a diagnostic helper and does not call the NERM REST API.
    """
    invoke_auth = os.getenv("NERM_INVOKE_AUTHORIZATION", "").strip()
    if not invoke_auth:
        return {"error": "nerm_api_error", "status": 400, "body": "NERM_INVOKE_AUTHORIZATION is not set"}
    token = invoke_auth
    parts = invoke_auth.split(maxsplit=1)
    if parts and parts[0].lower() == "bearer":
        token = parts[1] if len(parts) > 1 else ""
    token = token.strip()
    if not token:
        return {"error": "nerm_api_error", "status": 400, "body": "NERM_INVOKE_AUTHORIZATION token is empty"}
    try:
        claims = jwt.decode(token, options={"verify_signature": False})
    except Exception as exc:  # pragma: no cover
        return {"error": "nerm_api_error", "status": 400, "body": f"invalid JWT: {exc}"}
    return {"claims": claims}
