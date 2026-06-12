from pathlib import Path

from nerm.server import NermServer, build_fastmcp
from nerm.tools.registry import NERM_TOOLS


def test_build_fastmcp_falls_back_to_local_server_when_fastmcp_missing(monkeypatch) -> None:
    monkeypatch.setattr("nerm.server.FastMCP", None)
    app = build_fastmcp()
    assert isinstance(app, NermServer)
    assert len(app.tools) == len(NERM_TOOLS)


def test_build_fastmcp_registers_all_tools_when_fastmcp_available(monkeypatch) -> None:
    registered_names: list[str] = []
    captured_instructions: list[str | None] = []

    class FakeFastMCP:
        def __init__(self, name: str, instructions: str | None = None, **kwargs) -> None:  # noqa: ANN003
            self.name = name
            captured_instructions.append(instructions)

        def tool(self, name: str):  # noqa: ANN001
            def decorator(fn):  # noqa: ANN001
                registered_names.append(name)
                return fn

            return decorator

    monkeypatch.setattr("nerm.server.FastMCP", FakeFastMCP)
    monkeypatch.setattr("nerm.server._load_system_prompt", lambda: "prompt-body")
    app = build_fastmcp()
    assert isinstance(app, FakeFastMCP)
    assert app.name == "nerm-agent"
    assert captured_instructions == ["prompt-body"]
    assert set(registered_names) == set(NERM_TOOLS.keys())


def test_system_prompt_keeps_glossary_and_profile_type_routing_contract() -> None:
    prompt_path = Path(__file__).resolve().parents[2] / "app" / "Agent" / "system_prompt.txt"
    prompt = prompt_path.read_text(encoding="utf-8")

    required_markers = [
        "Business Glossary and Profile-Type Routing (MANDATORY)",
        "Role/User Type Glossary (MANDATORY)",
        "Portal Role:",
        "NeaccessRole",
        "Lifecycle Role:",
        "NeprofileRole",
        "Portal User:",
        "NeaccessUser",
        "Lifecycle User:",
        "NeprofileUser",
        "\"Collaboration\" means \"Portal\"",
        "Profile-Type First Decision Rule",
        "People alias mapping (MANDATORY)",
        "\"Person\", \"Persons\", \"People\", \"Non-Employee\", \"Non Employee\", and \"Worker\" as aliases for the canonical `People` profile type name",
        "Mandatory plan for \"active assignments\"",
        "Mandatory plan for \"active people\"",
        "Mandatory plan for any profile type + any status",
        "Mandatory plan for analytic requests (sort/rank/count/group)",
        "Organizations sorted by risk + assignment count pattern",
        "Audit Query (`nerm_query_audit_events`)",
        "event_type` (maps to payload key `type`): `Get`, `Post`, `Patch`, `Delete`",
        "Allowed filter keys: `subject_type`, `type`, `subject_id`, `workflow_name`, `workflow_uid`, `workflow_profile_type`, `profile_type`.",
        "Chart Generation (`nerm_generate_chart`)",
        "Supported request options:",
        "Per-series options: `label`, `chart_type` (`line`, `bar`, `pie`, `donut`, `scatter`, `area`, `horizontal_bar`, `histogram`, `box`, `grouped_bar`, `stacked_bar`, `multi_line`, `heatmap`)",
        "Rendering options: `title`, `x_label`, `y_label`, `width`, `height`, `dpi`, `show_grid`",
        "If x-axis values are date-based, sort chronologically before plotting.",
        "Output options: `embed_in_response` and `include_base64` (compatibility inputs).",
        "Chart delivery uses MCP image content blocks",
        "context-window overflow in remote-agent tool loops",
        "`embed_in_response` and `include_base64` are accepted for compatibility",
        "No duplicate broad pulls",
        "Relationship Graph for Analytics (MANDATORY)",
        "organization_assignments` on Organization profiles links to assignment records",
        "assignment_organization` on Assignment profiles links each assignment back to an organization label",
        "Fallback rule for reliability",
        "fall back to profile-type constrained `nerm_run_advanced_search` and ID-based correlation",
        "This rule applies to ANY status value",
        "Do NOT satisfy this request with only `nerm_list_profiles(status=Active)`",
        "resolve the intended profile type name to Profile Type ID",
    ]
    missing = [marker for marker in required_markers if marker not in prompt]
    assert not missing, f"system_prompt.txt is missing required routing markers: {missing}"
