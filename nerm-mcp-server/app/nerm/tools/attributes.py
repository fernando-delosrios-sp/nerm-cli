from nerm.client.endpoints import ATTRIBUTES
from nerm.schemas.attributes import normalize_attribute_item
from nerm.schemas.common import normalize_catalog_slice, pagination_validation_error
from nerm.tools.param_specs import (
    AttributeDataType,
    CatalogLimitInt32,
    Int32NonNegative,
    MetadataFlag,
    OptionalBaseUrl,
    OptionalBearerToken,
    OrderBy,
    ResourceId,
)
from nerm.tools._reference_catalog import (
    CATALOG_ATTRIBUTES,
    execute_with_nerm_error_json,
    get_catalog_cached,
)
from pydantic import ValidationError


def nerm_list_attributes(
    limit: CatalogLimitInt32 = 100,
    offset: Int32NonNegative = 0,
    order: OrderBy = None,
    label: str | None = None,
    data_type: AttributeDataType | None = None,
    metadata: MetadataFlag = None,
    nerm_base_url: OptionalBaseUrl = None,
    nerm_bearer_token: OptionalBearerToken = None,
) -> dict:
    """List attribute catalog entries used in profile and advanced-search rules.

    Use to discover relational attribute IDs and date-attribute metadata (including
    `neAttribute.date_format`) before building ProfileAttributeRule filters.
    """
    def _run() -> dict:
        try:
            bounded_limit, bounded_offset = normalize_catalog_slice(limit=limit, offset=offset)
        except ValidationError as exc:
            return pagination_validation_error(exc)
        catalog = get_catalog_cached(
            catalog_name=CATALOG_ATTRIBUTES,
            path=ATTRIBUTES,
            nerm_base_url=nerm_base_url,
            nerm_bearer_token=nerm_bearer_token,
        )
        filtered = [normalize_attribute_item(item) for item in catalog]
        if label:
            needle = label.strip().lower()
            filtered = [item for item in filtered if needle in str(item.get("label") or item.get("name") or "").lower()]
        if data_type:
            expected = data_type.strip().lower()
            filtered = [item for item in filtered if str(item.get("data_type") or item.get("type") or "").lower() == expected]
        if order:
            filtered = sorted(filtered, key=lambda item: str(item.get(order, "")))
        sliced = filtered[bounded_offset : bounded_offset + bounded_limit]
        response = {"items": sliced, "limit": bounded_limit, "offset": bounded_offset, "total": len(filtered)}
        if metadata is False:
            response.pop("total", None)
        return response

    return execute_with_nerm_error_json(_run)


def nerm_get_attribute(
    attribute_id: ResourceId,
    nerm_base_url: OptionalBaseUrl = None,
    nerm_bearer_token: OptionalBearerToken = None,
) -> dict:
    """Fetch one attribute definition by ID."""
    def _run() -> dict:
        catalog = get_catalog_cached(
            catalog_name=CATALOG_ATTRIBUTES,
            path=ATTRIBUTES,
            nerm_base_url=nerm_base_url,
            nerm_bearer_token=nerm_bearer_token,
        )
        for item in catalog:
            normalized = normalize_attribute_item(item)
            if normalized.get("id") == attribute_id:
                return normalized
        return {"error": "nerm_api_error", "status": 404, "body": f"attribute {attribute_id} not found"}

    return execute_with_nerm_error_json(_run)
