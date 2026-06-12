from __future__ import annotations

import json
import re
from dataclasses import dataclass

from nerm.evals.tool_selection_eval import ToolCall

_INPUT_RE = re.compile(r"tool_call_input tool=(?P<tool>[a-zA-Z0-9_]+) args=(?P<args>\{.*\}|\[.*\]|\".*\"|.*)$")


@dataclass
class CapturedTrace:
    calls: list[ToolCall]
    final_response: str = ""


def _parse_args(raw: str) -> dict[str, object]:
    text = raw.strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except Exception:  # noqa: BLE001
        return {"_raw": text}
    return parsed if isinstance(parsed, dict) else {"_value": parsed}


def extract_tool_calls_from_log_lines(lines: list[str]) -> list[ToolCall]:
    calls: list[ToolCall] = []
    for line in lines:
        match = _INPUT_RE.search(line)
        if not match:
            continue
        tool = match.group("tool")
        args = _parse_args(match.group("args"))
        calls.append(ToolCall(name=tool, arguments=args))
    return calls


def build_trace_payload(lines: list[str], final_response: str = "") -> dict[str, object]:
    calls = extract_tool_calls_from_log_lines(lines)
    return {
        "calls": [{"name": call.name, "arguments": call.arguments} for call in calls],
        "final_response": final_response,
    }
