from nerm.client.endpoints import PROFILES
from nerm.client.http_client import NermHttpClient
from nerm.errors import NermApiError
from nerm.schemas.common import normalize_pagination, pagination_validation_error
from nerm.schemas.profiles import normalize_profile_item
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
    ProfileStatus,
    ResourceId,
)
from nerm.tools._reference_catalog import execute_with_nerm_error_json, extract_list_records, resolve_connection
from pydantic import ValidationError


def nerm_list_profiles(
    limit: Int32Positive = 100,
    offset: Int32NonNegative = 0,
    force_all: ForceAllFlag = False,
    order: OrderBy = None,
    exclude_attributes: bool | None = None,
    name: str | None = None,
    profile_type_id: str | None = None,
    status: ProfileStatus | None = None,
    metadata: MetadataFlag = None,
    after_id: str | None = None,
    updated_after: str | None = None,
    nerm_base_url: OptionalBaseUrl = None,
    nerm_bearer_token: OptionalBearerToken = None,
) -> dict:
    """List profile records, including Assignment profiles used for engagement questions.

    Use for profile/business state lookups (assignments, people, organizations, etc.).
    Do not use delegations tools for assignment queries.
    Prefer nerm_run_advanced_search for ranking/grouping or multi-filter queries.
    For single profile-type requests without extra conditions (simple totals or plain listings),
    resolve profile type ID and use nerm_list_profiles(profile_type_id=...) first.
    When `metadata=true`, use response `total` for count answers.
    Relationship hints: `organization_assignments` links organization -> assignments and
    `assignment_organization` links assignment -> organization.
    """
    def _is_no_profiles_found_error(exc: NermApiError) -> bool:
        if exc.status not in {400, 404}:
            return False
        return "no profiles found" in str(exc.body or "").lower()

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
            if order:
                params["order"] = order
            if exclude_attributes is not None:
                params["exclude_attributes"] = exclude_attributes
            if name:
                params["name"] = name
            if profile_type_id:
                params["profile_type_id"] = profile_type_id
            if status:
                params["status"] = status
            if after_id:
                params["after_id"] = after_id
            if updated_after:
                params["updated_after"] = updated_after
            try:
                return client.request("GET", PROFILES, timeout=15.0, params=params)
            except NermApiError as exc:
                # Treat offset overflow as end-of-pagination, not a hard tool failure.
                if _is_no_profiles_found_error(exc):
                    return {"profiles": []}
                raise

        def _parse_page(payload: object) -> list[dict]:
            if not isinstance(payload, dict):
                return []
            page_items = extract_list_records(payload, preferred_keys=("profiles",))
            return [normalize_profile_item(item) for item in page_items]

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


def nerm_get_profile(
    profile_id: ResourceId,
    nerm_base_url: OptionalBaseUrl = None,
    nerm_bearer_token: OptionalBearerToken = None,
) -> dict:
    """Fetch a single profile by ID.

    Use after resolving profile IDs from list/search results.
    """
    def _run() -> dict:
        base_url, bearer_token = resolve_connection(nerm_base_url=nerm_base_url, nerm_bearer_token=nerm_bearer_token)
        client = NermHttpClient(base_url=base_url, bearer_token=bearer_token)
        payload = client.request("GET", f"{PROFILES}/{profile_id}", timeout=15.0)
        return normalize_profile_item(payload) if isinstance(payload, dict) else payload

    return execute_with_nerm_error_json(_run)
