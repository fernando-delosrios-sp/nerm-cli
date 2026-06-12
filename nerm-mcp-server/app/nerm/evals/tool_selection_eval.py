from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ToolCall:
    name: str
    arguments: dict[str, object] = field(default_factory=dict)


@dataclass
class ToolSelectionCase:
    case_id: str
    prompt: str
    required_tools: list[str] = field(default_factory=list)
    forbidden_tools: list[str] = field(default_factory=list)
    max_calls: int | None = None
    tool_max_calls: dict[str, int] = field(default_factory=dict)
    required_argument_keys: dict[str, list[str]] = field(default_factory=dict)
    forbidden_argument_keys: dict[str, list[str]] = field(default_factory=dict)
    required_response_substrings: list[str] = field(default_factory=list)


@dataclass
class ToolSelectionResult:
    case_id: str
    passed: bool
    violations: list[str]
    observed_call_count: int
    observed_tools: list[str]


def evaluate_tool_selection_case(
    case: ToolSelectionCase,
    calls: list[ToolCall],
    final_response_text: str = "",
) -> ToolSelectionResult:
    violations: list[str] = []
    observed_tools = [call.name for call in calls]

    for tool in case.required_tools:
        if tool not in observed_tools:
            violations.append(f"required tool not called: {tool}")
    for tool in case.forbidden_tools:
        if tool in observed_tools:
            violations.append(f"forbidden tool was called: {tool}")

    if case.max_calls is not None and len(calls) > case.max_calls:
        violations.append(f"call budget exceeded: {len(calls)} > {case.max_calls}")

    for tool, max_count in case.tool_max_calls.items():
        count = sum(1 for call in calls if call.name == tool)
        if count > max_count:
            violations.append(f"tool call budget exceeded for {tool}: {count} > {max_count}")

    for tool, required_keys in case.required_argument_keys.items():
        for idx, call in enumerate(calls):
            if call.name != tool:
                continue
            missing = [key for key in required_keys if key not in call.arguments]
            if missing:
                violations.append(f"{tool} call[{idx}] missing required argument keys: {missing}")

    for tool, forbidden_keys in case.forbidden_argument_keys.items():
        for idx, call in enumerate(calls):
            if call.name != tool:
                continue
            present = [key for key in forbidden_keys if key in call.arguments]
            if present:
                violations.append(f"{tool} call[{idx}] used forbidden argument keys: {present}")

    lowered_response = final_response_text.lower()
    for token in case.required_response_substrings:
        if token.lower() not in lowered_response:
            violations.append(f"final response missing required substring: {token}")

    return ToolSelectionResult(
        case_id=case.case_id,
        passed=not violations,
        violations=violations,
        observed_call_count=len(calls),
        observed_tools=observed_tools,
    )
