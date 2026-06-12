from nerm.tools.registry import NERM_TOOLS


def test_tool_registry_count() -> None:
    assert len(NERM_TOOLS) == 36
