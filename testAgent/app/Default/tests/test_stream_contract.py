import logging
import sys
import types
import unittest

# Runtime dependency stubs so tests can import main.py helpers.
strands_mod = types.ModuleType("strands")
strands_mod.Agent = object
strands_mod.tool = lambda fn: fn
sys.modules["strands"] = strands_mod

bedrock_pkg = types.ModuleType("bedrock_agentcore")
bedrock_runtime_mod = types.ModuleType("bedrock_agentcore.runtime")


class DummyBedrockAgentCoreApp:
    def __init__(self) -> None:
        self.logger = logging.getLogger("test")

    def entrypoint(self, fn):
        return fn

    def run(self, *args, **kwargs):
        return None


bedrock_runtime_mod.BedrockAgentCoreApp = DummyBedrockAgentCoreApp
sys.modules["bedrock_agentcore"] = bedrock_pkg
sys.modules["bedrock_agentcore.runtime"] = bedrock_runtime_mod

model_pkg = types.ModuleType("model")
model_load_mod = types.ModuleType("model.load")
model_load_mod.load_model = lambda: object()
sys.modules["model"] = model_pkg
sys.modules["model.load"] = model_load_mod

mcp_client_pkg = types.ModuleType("mcp_client")
mcp_client_client_mod = types.ModuleType("mcp_client.client")
mcp_client_client_mod.get_streamable_http_mcp_client = lambda session_key, recreate=False: None
mcp_client_client_mod.evict_streamable_http_mcp_client = lambda session_key: None
sys.modules["mcp_client"] = mcp_client_pkg
sys.modules["mcp_client.client"] = mcp_client_client_mod

from main import (
    _event_data_to_text,
    _markdown_table_from_structured_payloads,
    _normalize_tool_result_contract,
    _prompt_requires_mcp_grounding,
    _sanitize_user_text,
)


class StreamContractTests(unittest.TestCase):
    def test_contract_fields_are_preserved(self) -> None:
        tool_result = {
            "content": [{"type": "text", "text": "ok"}],
            "structuredContent": {"status": "ok", "total": 3},
            "isError": True,
        }
        content, structured_content, is_error = _normalize_tool_result_contract(tool_result)
        self.assertEqual(content, [{"type": "text", "text": "ok"}])
        self.assertEqual(structured_content, {"status": "ok", "total": 3})
        self.assertTrue(is_error)

    def test_event_data_to_text(self) -> None:
        self.assertEqual(_event_data_to_text("x"), "x")
        self.assertEqual(_event_data_to_text(10), "10")
        self.assertEqual(_event_data_to_text({"a": 1}), '{"a": 1}')

    def test_markdown_table_from_structured_payloads(self) -> None:
        payloads = [
            {"data": {"items": [{"id": "1", "name": "Organizations", "archived": False}]}},
            {"data": {"items": [{"id": "2", "name": "People", "archived": True}]}}
        ]
        table = _markdown_table_from_structured_payloads(payloads)
        self.assertIn("| ID | Name | Archived |", table)
        self.assertIn("| 1 | Organizations | false |", table)
        self.assertIn("| 2 | People | true |", table)

    def test_prompt_requires_grounding(self) -> None:
        self.assertTrue(_prompt_requires_mcp_grounding("show report totals"))
        self.assertFalse(_prompt_requires_mcp_grounding("hello there"))

    def test_sanitize_user_text(self) -> None:
        self.assertEqual(_sanitize_user_text("Tool #1: nerm_list\nhello"), "hello")
        self.assertEqual(_sanitize_user_text("data:image/png;base64,abc"), "")


if __name__ == "__main__":
    unittest.main()
