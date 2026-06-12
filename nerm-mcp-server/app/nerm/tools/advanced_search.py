from nerm.client.endpoints import ADVANCED_SEARCH_RUN
from nerm.client.http_client import NermHttpClient
from nerm.schemas.advanced_search import AdvancedSearchPayload
from nerm.schemas.profiles import normalize_profile_item
from nerm.spec_contract import ADVANCED_SEARCH_REQUIRED_KEYS, ADVANCED_SEARCH_SQL_STYLE_KEYS
from nerm.tools._reference_catalog import execute_with_nerm_error_json, extract_list_records, resolve_connection
from pydantic import ValidationError


def nerm_run_advanced_search(
    advanced_search: AdvancedSearchPayload,
    nerm_base_url: str | None = None,
    nerm_bearer_token: str | None = None,
) -> dict:
    """Run filtered profile search with explicit NERM rule objects.

    Prefer this for targeted profile/assignment queries that need multiple filters,
    and for ranking/counting/grouping analytics.
    Do not default to this for single profile-type requests without extra conditions
    when nerm_list_profiles(profile_type_id=...) can answer directly.
    For "active assignments", include both ProfileTypeRule (Assignment profile type ID)
    and ProfileStatusRule ("Active").
    For org assignment analytics, use this with profile-type-constrained rules, then
    correlate relationship attributes (`organization_assignments`, `assignment_organization`)
    as needed. If derived links disagree, trust constrained search results.
    Do not use SQL-style keys; use condition_rules_attributes schema.
    DateAttribute enforcement:
    - Resolve date-attribute metadata first via `nerm_list_attributes` and/or `nerm_get_attribute`.
    - Read the expected date format from `neAttribute.date_format`.
    - Normalize date values to `neAttribute.date_format` before building rules.
    - For DateAttribute comparisons, use only `after` and `before` operators.
      Do not use `>`, `<`, `>=`, or `<=` for date conditions.
    """
    def _run() -> dict:
        raw_input = (
            advanced_search.model_dump(exclude_none=True, mode="json")
            if isinstance(advanced_search, AdvancedSearchPayload)
            else advanced_search
        )
        if not isinstance(raw_input, dict):
            return {
                "error": "invalid_advanced_search_spec",
                "message": "advanced_search must be an object matching NERM advanced search schema.",
            }
        if any(key in raw_input for key in ADVANCED_SEARCH_SQL_STYLE_KEYS):
            return {
                "error": "invalid_advanced_search_spec",
                "message": "Use NERM condition_rules_attributes schema, not SQL-style clauses.",
            }
        normalized = raw_input.get("advanced_search", raw_input)
        if not isinstance(normalized, dict):
            return {
                "error": "invalid_advanced_search_spec",
                "message": "advanced_search must be an object matching NERM advanced search schema.",
            }
        missing = [key for key in ADVANCED_SEARCH_REQUIRED_KEYS if key not in normalized]
        if missing:
            return {
                "error": "invalid_advanced_search_spec",
                "message": f"advanced_search missing required keys: {missing}",
            }
        rules = normalized.get("condition_rules_attributes")
        if isinstance(rules, list) and len(rules) == 0:
            return {
                "error": "insufficient_advanced_search_filters",
                "message": "Provide at least one condition rule to avoid broad profile listing.",
                "guidance": {
                    "example_rules": [
                        {"type": "ProfileStatusRule", "comparison_operator": "==", "value": "Active"},
                        {
                            "type": "ProfileAttributeRule",
                            "condition_object_type": "TextFieldAttribute",
                            "condition_object_id": "<ne_attribute.id UUID>",
                            "comparison_operator": "==",
                            "value": "Contractor",
                        },
                    ]
                },
            }
        try:
            normalized = AdvancedSearchPayload.validate_inner_payload(normalized)
        except ValidationError as exc:
            return {
                "error": "invalid_advanced_search_spec",
                "message": "advanced_search failed schema validation for condition_rules_attributes.",
                "details": exc.errors(include_url=False),
            }
        except ValueError as exc:
            return {
                "error": "invalid_advanced_search_spec",
                "message": str(exc),
            }
        base_url, bearer_token = resolve_connection(nerm_base_url=nerm_base_url, nerm_bearer_token=nerm_bearer_token)
        client = NermHttpClient(base_url=base_url, bearer_token=bearer_token)
        body = {"advanced_search": normalized}
        payload = client.request("POST", ADVANCED_SEARCH_RUN, timeout=30.0, json=body)
        if not isinstance(payload, dict):
            return payload
        page_items = extract_list_records(payload, preferred_keys=("profiles",))
        if page_items:
            payload["items"] = [normalize_profile_item(item) for item in page_items]
        return payload

    return execute_with_nerm_error_json(_run)
