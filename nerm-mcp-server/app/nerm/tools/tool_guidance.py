"""Reusable tool-guidance snippets to keep docstrings and prompts aligned."""

from __future__ import annotations


CHART_USAGE = """
When to call: only call `nerm_generate_chart` when the user explicitly asks for a chart, graph, or visualization.
Do not call it for plain tabular/list/count responses unless the user asks for visual output.
In user-facing responses, do not emit raw base64 strings or local file paths; rely on MCP image block rendering.
"""


def append_tool_guidance(doc: str | None, *segments: str) -> str:
    """Append normalized guidance segments to a base docstring."""
    base = (doc or "").rstrip()
    extra = "\n".join(part.strip() for part in segments if part and part.strip())
    return f"{base}\n\n{extra}" if extra else base

