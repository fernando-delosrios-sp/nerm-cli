from nerm.evals.trace_capture import build_trace_payload, extract_tool_calls_from_log_lines


def test_extract_tool_calls_from_log_lines() -> None:
    lines = [
        "2026-01-01 10:00:00 tool_call_input tool=nerm_list_roles args={\"limit\": 50, \"offset\": 0}",
        "2026-01-01 10:00:01 tool_call_output tool=nerm_list_roles output={\"items\": []}",
        "2026-01-01 10:00:02 tool_call_input tool=nerm_list_user_roles args={\"role_id\": \"abc\"}",
    ]
    calls = extract_tool_calls_from_log_lines(lines)
    assert [c.name for c in calls] == ["nerm_list_roles", "nerm_list_user_roles"]
    assert calls[0].arguments["limit"] == 50
    assert calls[1].arguments["role_id"] == "abc"


def test_build_trace_payload_includes_final_response() -> None:
    lines = [
        "tool_call_input tool=nerm_get_user args={\"user_id\": \"u-1\"}",
    ]
    payload = build_trace_payload(lines, final_response="Done.")
    assert payload["final_response"] == "Done."
    assert payload["calls"] == [{"name": "nerm_get_user", "arguments": {"user_id": "u-1"}}]
