from nerm.test_agent import suggest_tool_call


def test_suggest_tool_call_profiles() -> None:
    suggestion = suggest_tool_call("show me profiles")
    assert suggestion is not None
    assert suggestion.name == "nerm_list_profiles"


def test_suggest_tool_call_advanced_search() -> None:
    suggestion = suggest_tool_call("run advanced search")
    assert suggestion is not None
    assert suggestion.name == "nerm_run_advanced_search"
    assert "advanced_search" in suggestion.arguments


def test_suggest_tool_call_returns_none_for_unmapped_prompt() -> None:
    assert suggest_tool_call("hello there") is None
