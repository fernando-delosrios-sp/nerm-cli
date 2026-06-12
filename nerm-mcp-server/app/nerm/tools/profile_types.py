from nerm.client.endpoints import PROFILE_TYPES
from nerm.schemas.profile_types import normalize_profile_type_item
from nerm.schemas.common import normalize_catalog_slice, pagination_validation_error
from nerm.tools.param_specs import CatalogLimitInt32, Int32NonNegative, MetadataFlag, OptionalBaseUrl, OptionalBearerToken, OrderBy, ResourceId
from nerm.tools._reference_catalog import (
    CATALOG_PROFILE_TYPES,
    execute_with_nerm_error_json,
    get_catalog_cached,
)
from pydantic import ValidationError


def nerm_list_profile_types(
    limit: CatalogLimitInt32 = 100,
    offset: Int32NonNegative = 0,
    order: OrderBy = None,
    name: str | None = None,
    archived: bool | None = None,
    metadata: MetadataFlag = None,
    nerm_base_url: OptionalBaseUrl = None,
    nerm_bearer_token: OptionalBearerToken = None,
) -> dict:
    """List profile type catalog entries (Assignments, People, Organizations, etc.).

    Use this first when a request implies a specific business profile type.
    Resolve profile type ID here, then apply it as a required filter in
    nerm_run_advanced_search for status/ranking/count/group requests.
    """
    def _run() -> dict:
        try:
            bounded_limit, bounded_offset = normalize_catalog_slice(limit=limit, offset=offset)
        except ValidationError as exc:
            return pagination_validation_error(exc)
        catalog = get_catalog_cached(
            catalog_name=CATALOG_PROFILE_TYPES,
            path=PROFILE_TYPES,
            nerm_base_url=nerm_base_url,
            nerm_bearer_token=nerm_bearer_token,
        )
        filtered = [normalize_profile_type_item(item) for item in catalog]
        if name:
            needle = name.strip().lower()
            filtered = [item for item in filtered if needle in str(item.get("name") or "").lower()]
        if archived is not None:
            filtered = [item for item in filtered if bool(item.get("archived")) is archived]
        if order:
            filtered = sorted(filtered, key=lambda item: str(item.get(order, "")))
        sliced = filtered[bounded_offset : bounded_offset + bounded_limit]
        response = {"items": sliced, "limit": bounded_limit, "offset": bounded_offset, "total": len(filtered)}
        if metadata is False:
            response.pop("total", None)
        return response

    return execute_with_nerm_error_json(_run)


def nerm_get_profile_type(
    profile_type_id: ResourceId,
    nerm_base_url: OptionalBaseUrl = None,
    nerm_bearer_token: OptionalBearerToken = None,
) -> dict:
    """Fetch one profile type by ID.

    Use after resolving candidate profile type IDs from nerm_list_profile_types.
    """
    def _run() -> dict:
        catalog = get_catalog_cached(
            catalog_name=CATALOG_PROFILE_TYPES,
            path=PROFILE_TYPES,
            nerm_base_url=nerm_base_url,
            nerm_bearer_token=nerm_bearer_token,
        )
        for item in catalog:
            normalized = normalize_profile_type_item(item)
            if normalized.get("id") == profile_type_id:
                return normalized
        return {"error": "nerm_api_error", "status": 404, "body": f"profile type {profile_type_id} not found"}

    return execute_with_nerm_error_json(_run)
