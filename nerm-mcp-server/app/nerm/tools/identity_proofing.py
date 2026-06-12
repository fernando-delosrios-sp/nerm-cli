from nerm.client.endpoints import IDENTITY_PROOFING_RESULTS
from nerm.client.http_client import NermHttpClient
from nerm.schemas.common import normalize_pagination, pagination_validation_error
from nerm.schemas.identity_proofing import normalize_identity_proofing_item
from nerm.services.pagination import (
    collect_paginated_items,
    unique_item_count,
)
from nerm.tools.param_specs import (
    ForceAllFlag,
    IdentityProofingResult,
    Int32NonNegative,
    Int32Positive,
    MetadataFlag,
    OptionalBaseUrl,
    OptionalBearerToken,
    OrderBy,
)
from nerm.tools._reference_catalog import execute_with_nerm_error_json, extract_list_records, resolve_connection
from pydantic import ValidationError


def nerm_list_identity_proofing_results(
    limit: Int32Positive = 100,
    offset: Int32NonNegative = 0,
    force_all: ForceAllFlag = False,
    order: OrderBy = None,
    profile_id: str | None = None,
    workflow_session_id: str | None = None,
    result: IdentityProofingResult | None = None,
    metadata: MetadataFlag = None,
    nerm_base_url: OptionalBaseUrl = None,
    nerm_bearer_token: OptionalBearerToken = None,
) -> dict:
    """List identity proofing result records for profiles/workflow sessions.

    Use for proofing outcome checks; handle sensitive values carefully in responses.
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
            if order:
                params["order"] = order
            if profile_id:
                params["profile_id"] = profile_id
            if workflow_session_id:
                params["workflow_session_id"] = workflow_session_id
            if result:
                params["result"] = result
            return client.request("GET", IDENTITY_PROOFING_RESULTS, timeout=15.0, params=params)

        def _parse_page(payload: object) -> list[dict]:
            if not isinstance(payload, dict):
                return []
            page_items = extract_list_records(payload, preferred_keys=("identity_proofing_results",))
            return [normalize_identity_proofing_item(item) for item in page_items]

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
