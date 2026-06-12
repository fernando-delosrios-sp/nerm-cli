from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ToolCallSuggestion:
    name: str
    arguments: dict[str, object]


def suggest_tool_call(user_text: str) -> ToolCallSuggestion | None:
    text = user_text.strip().lower()
    if not text:
        return None
    if "profile type" in text:
        return ToolCallSuggestion(name="nerm_list_profile_types", arguments={"limit": 10, "offset": 0})
    if "attribute" in text:
        return ToolCallSuggestion(name="nerm_list_attributes", arguments={"limit": 10, "offset": 0})
    if "user" in text:
        return ToolCallSuggestion(name="nerm_list_users", arguments={"limit": 10, "offset": 0})
    if "profile" in text:
        return ToolCallSuggestion(name="nerm_list_profiles", arguments={"limit": 10, "offset": 0})
    if "audit" in text:
        return ToolCallSuggestion(
            name="nerm_query_audit_events",
            arguments={"subject_type": "WorkflowSession", "limit": 5, "offset": 0},
        )
    if "advanced search" in text:
        return ToolCallSuggestion(
            name="nerm_run_advanced_search",
            arguments={
                "advanced_search": {
                    "condition_rules_attributes": [
                        {"type": "ProfileStatusRule", "comparison_operator": "==", "value": "Active"}
                    ]
                }
            },
        )
    return None
