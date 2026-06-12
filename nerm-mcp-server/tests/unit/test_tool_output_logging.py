import logging
from types import SimpleNamespace

from mcp.server.fastmcp.utilities.context_injection import find_context_parameter
from mcp.types import CallToolResult, ImageContent, TextContent
from nerm.tools.registry import _wrap_tool


def test_wrap_tool_logs_output_payload(caplog) -> None:
    def fake_tool() -> dict:
        return {"ok": True, "token": "abc123"}

    wrapped = _wrap_tool("fake_tool", fake_tool)
    with caplog.at_level(logging.DEBUG, logger="nerm.tools"):
        result = wrapped()

    assert isinstance(result, CallToolResult)
    dumped = result.model_dump(mode="json")
    assert dumped["isError"] is False
    assert dumped["structuredContent"]["ok"] is True
    assert "tool_call_output tool=fake_tool" in caplog.text
    assert '"ok": true' in caplog.text
    assert "<redacted>" in caplog.text
    assert "abc123" not in caplog.text


def test_wrap_tool_injects_auth_from_request_headers() -> None:
    captured: dict[str, str] = {}

    def fake_tool(nerm_base_url: str | None = None, nerm_bearer_token: str | None = None) -> dict:
        captured["base_url"] = str(nerm_base_url)
        captured["token"] = str(nerm_bearer_token)
        return {"ok": True}

    class FakeRequest:
        headers = {
            "X-NERM-URL": "https://tenant.example.com",
            "X-NERM-Authorization": "Bearer test-token",
        }

    class FakeRequestContext:
        request = FakeRequest()

    class FakeCtx:
        request_context = FakeRequestContext()

    wrapped = _wrap_tool("fake_tool", fake_tool)
    result = wrapped(ctx=FakeCtx())

    assert isinstance(result, CallToolResult)
    assert result.model_dump(mode="json")["isError"] is False
    assert captured["base_url"] == "https://tenant.example.com/api"
    assert captured["token"] == "Bearer test-token"


def test_wrap_tool_exposes_ctx_annotation_for_fastmcp_injection() -> None:
    def fake_tool(nerm_base_url: str | None = None, nerm_bearer_token: str | None = None) -> dict:
        return {"ok": True}

    wrapped = _wrap_tool("fake_tool", fake_tool)
    assert find_context_parameter(wrapped) == "ctx"


def test_wrap_tool_logs_output_at_info_when_verbose_trace_enabled(monkeypatch, caplog) -> None:
    def fake_tool() -> dict:
        return {"ok": True}

    monkeypatch.setattr(
        "nerm.tools.registry.get_settings",
        lambda: SimpleNamespace(nerm_verbose_trace=True, nerm_trace_max_bytes=4096),
    )
    wrapped = _wrap_tool("fake_tool", fake_tool)
    with caplog.at_level(logging.INFO, logger="nerm.tools"):
        wrapped()
    assert "tool_call_output tool=fake_tool" in caplog.text


def test_wrap_tool_logs_image_outputs_without_dumping_binary(caplog) -> None:
    def fake_tool() -> CallToolResult:
        return CallToolResult(
            content=[
                TextContent(type="text", text='{"status":"success"}'),
                ImageContent(type="image", mimeType="image/png", data="ZmFrZWJhc2U2NA=="),
            ],
            isError=False,
        )

    wrapped = _wrap_tool("fake_tool", fake_tool)
    with caplog.at_level(logging.DEBUG, logger="nerm.tools"):
        result = wrapped()

    assert isinstance(result, CallToolResult)
    assert "tool_call_output tool=fake_tool" in caplog.text
    assert "<base64_image len=21>" in caplog.text
    assert "ZmFrZWJhc2U2NA==" not in caplog.text


