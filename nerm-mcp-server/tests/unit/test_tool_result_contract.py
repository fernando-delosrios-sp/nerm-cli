from mcp.types import CallToolResult, TextContent
from nerm.tools.registry import NERM_TOOLS, _build_wrapped_tools


def _dump(result: CallToolResult) -> dict:
    return result.model_dump(mode="json")


def test_all_registered_tools_emit_standard_success_contract() -> None:
    raw_tools = {name: (lambda tool_name=name: {"tool": tool_name, "ok": True}) for name in NERM_TOOLS}
    wrapped = _build_wrapped_tools(raw_tools)

    assert set(wrapped.keys()) == set(NERM_TOOLS.keys())
    for name, tool in wrapped.items():
        result = tool()
        assert isinstance(result, CallToolResult), name
        dumped = _dump(result)
        assert dumped["isError"] is False, name
        assert isinstance(dumped["content"], list) and dumped["content"], name
        assert dumped["content"][0]["type"] == "text", name
        assert "structuredContent" in dumped, name
        assert dumped["structuredContent"]["status"] == "success", name
        assert dumped["structuredContent"]["tool"] == name, name


def test_all_registered_tools_emit_standard_error_contract() -> None:
    raw_tools = {
        name: (lambda tool_name=name: {"error": "simulated_failure", "message": f"{tool_name} failed"})
        for name in NERM_TOOLS
    }
    wrapped = _build_wrapped_tools(raw_tools)

    for name, tool in wrapped.items():
        result = tool()
        dumped = _dump(result)
        assert dumped["isError"] is True, name
        assert dumped["content"][0]["type"] == "text", name
        assert dumped["structuredContent"]["status"] == "error", name
        assert dumped["structuredContent"]["error"] == "simulated_failure", name
        assert dumped["structuredContent"]["message"] == f"{name} failed", name


def test_all_registered_tools_passthrough_call_tool_result() -> None:
    def _passthrough() -> CallToolResult:
        return CallToolResult(
            content=[TextContent(type="text", text='{"status":"success","source":"passthrough"}')],
            structuredContent={"status": "success", "source": "passthrough"},
            isError=False,
        )

    wrapped = _build_wrapped_tools({name: _passthrough for name in NERM_TOOLS})
    for name, tool in wrapped.items():
        result = tool()
        dumped = _dump(result)
        assert dumped["isError"] is False, name
        assert dumped["structuredContent"]["source"] == "passthrough", name
