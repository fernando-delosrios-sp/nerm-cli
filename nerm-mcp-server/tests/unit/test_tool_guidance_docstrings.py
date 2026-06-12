from nerm.tools.advanced_search import nerm_run_advanced_search
from nerm.tools.audit import nerm_query_audit_events
from nerm.tools.charts import nerm_generate_chart
from nerm.tools.delegations import nerm_create_delegation, nerm_list_delegations, nerm_update_delegation
from nerm.tools.profile_types import nerm_list_profile_types
from nerm.tools.profiles import nerm_list_profiles
from nerm.tools.roles import nerm_list_roles
from nerm.tools.users import nerm_list_user_roles, nerm_list_users


def test_tool_docstrings_keep_routing_and_relationship_guidance() -> None:
    required_markers = {
        nerm_list_profile_types: [
            "Resolve profile type ID",
            "nerm_run_advanced_search",
        ],
        nerm_list_profiles: [
            "Do not use delegations tools for assignment queries.",
            "organization_assignments",
            "assignment_organization",
        ],
        nerm_run_advanced_search: [
            "ranking/counting/grouping analytics",
            "Do not use SQL-style keys",
            "Resolve date-attribute metadata first",
            "Read the expected date format from `neAttribute.date_format`",
            "Normalize date values to `neAttribute.date_format`",
            "use only `after` and `before` operators",
        ],
        nerm_query_audit_events: [
            "event_type/type: Get, Post, Patch, Delete",
            "event_type` maps to payload key `type`",
            "workflow_name/workflow_uid/workflow_profile_type are workflow-session oriented filters.",
            "API allows at most 5 non-pagination filters.",
        ],
        nerm_generate_chart: [
            "Supported chart types: `line`, `bar`, `pie`, `donut`, `scatter`, `area`",
            "`embed_in_response`",
            "`include_base64`",
            "MCP image content block",
            "`title`, `x_label`, `y_label`, `width`, `height`, `dpi`, `show_grid`",
            "If x-axis values are date-based (ISO date/date-time strings), sort chronologically",
        ],
        nerm_list_delegations: [
            "Do not use for assignment/profile analytics.",
        ],
        nerm_create_delegation: [
            "exact key `expiration`",
        ],
        nerm_update_delegation: [
            "Do not use `end_date`, `expiration_date`, or `expires_at`.",
        ],
        nerm_list_roles: [
            "Portal/Collaboration role == `NeaccessRole`",
            "Lifecycle role == `NeprofileRole`",
        ],
        nerm_list_user_roles: [
            "Portal user == `NeaccessUser`",
            "Lifecycle user ==",
            "Portal/Collaboration role == `NeaccessRole`",
        ],
        nerm_list_users: [
            "Portal user == `NeaccessUser`",
            "Lifecycle user ==",
            "\"Collaboration\" refers to portal context.",
        ],
    }

    missing: dict[str, list[str]] = {}
    for fn, markers in required_markers.items():
        doc = fn.__doc__ or ""
        missing_markers = [marker for marker in markers if marker not in doc]
        if missing_markers:
            missing[fn.__name__] = missing_markers
    assert not missing, f"tool docstrings are missing required markers: {missing}"
