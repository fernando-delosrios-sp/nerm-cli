from nerm.evals.tool_selection_eval import ToolCall, ToolSelectionCase, evaluate_tool_selection_case


def test_eval_detects_forbidden_tool_and_budget() -> None:
    case = ToolSelectionCase(
        case_id="active_assignments_routing",
        prompt="show all active assignments",
        required_tools=["nerm_list_profile_types", "nerm_run_advanced_search"],
        forbidden_tools=["nerm_list_delegations"],
        max_calls=3,
    )
    calls = [
        ToolCall(name="nerm_list_profile_types", arguments={"name": "Assignment"}),
        ToolCall(name="nerm_list_delegations", arguments={"limit": 50}),
        ToolCall(name="nerm_run_advanced_search", arguments={"advanced_search": {"condition_rules_attributes": []}}),
        ToolCall(name="nerm_list_profiles", arguments={"status": "Active"}),
    ]
    result = evaluate_tool_selection_case(case, calls)
    assert result.passed is False
    assert any("forbidden tool was called: nerm_list_delegations" in v for v in result.violations)
    assert any("call budget exceeded" in v for v in result.violations)


def test_eval_passes_for_compact_role_user_flow() -> None:
    case = ToolSelectionCase(
        case_id="nerm_admin_users",
        prompt="show all users with the NERM Administrator role",
        required_tools=["nerm_list_user_roles"],
        max_calls=3,
        tool_max_calls={"nerm_get_user": 0, "nerm_get_role": 0},
        required_argument_keys={"nerm_list_user_roles": ["role_id"]},
    )
    calls = [
        ToolCall(name="nerm_list_roles", arguments={"limit": 100}),
        ToolCall(name="nerm_list_user_roles", arguments={"role_id": "c0c847df-c086-4707-a424-6bfe65ad17fe"}),
    ]
    result = evaluate_tool_selection_case(case, calls, final_response_text="Found 7 users with NERM Administrator role")
    assert result.passed is True
    assert result.violations == []
