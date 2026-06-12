from __future__ import annotations

import argparse
import json
from pathlib import Path

from nerm.evals.tool_selection_eval import (
    ToolCall,
    ToolSelectionCase,
    evaluate_tool_selection_case,
)


def _load_cases(path: Path) -> list[ToolSelectionCase]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("cases file must contain a JSON array")
    cases: list[ToolSelectionCase] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        cases.append(
            ToolSelectionCase(
                case_id=str(item["case_id"]),
                prompt=str(item.get("prompt", "")),
                required_tools=list(item.get("required_tools", [])),
                forbidden_tools=list(item.get("forbidden_tools", [])),
                max_calls=item.get("max_calls"),
                tool_max_calls=dict(item.get("tool_max_calls", {})),
                required_argument_keys=dict(item.get("required_argument_keys", {})),
                forbidden_argument_keys=dict(item.get("forbidden_argument_keys", {})),
                required_response_substrings=list(item.get("required_response_substrings", [])),
            )
        )
    return cases


def _load_trace(path: Path) -> tuple[list[ToolCall], str]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    calls_raw = raw.get("calls", [])
    response = str(raw.get("final_response", ""))
    calls: list[ToolCall] = []
    if isinstance(calls_raw, list):
        for entry in calls_raw:
            if not isinstance(entry, dict):
                continue
            calls.append(
                ToolCall(
                    name=str(entry.get("name", "")),
                    arguments=dict(entry.get("arguments", {})),
                )
            )
    return calls, response


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate LLM tool-selection traces against declarative cases.")
    parser.add_argument("--cases", required=True, help="Path to JSON array of tool-selection test cases.")
    parser.add_argument(
        "--traces-dir",
        required=True,
        help="Directory containing trace JSON files named <case_id>.json.",
    )
    args = parser.parse_args()

    cases_path = Path(args.cases).resolve()
    traces_dir = Path(args.traces_dir).resolve()
    cases = _load_cases(cases_path)

    failed = 0
    for case in cases:
        trace_path = traces_dir / f"{case.case_id}.json"
        if not trace_path.exists():
            print(json.dumps({"case_id": case.case_id, "passed": False, "violations": ["missing trace file"]}))
            failed += 1
            continue
        calls, final_response = _load_trace(trace_path)
        result = evaluate_tool_selection_case(case, calls, final_response_text=final_response)
        print(
            json.dumps(
                {
                    "case_id": result.case_id,
                    "passed": result.passed,
                    "observed_call_count": result.observed_call_count,
                    "observed_tools": result.observed_tools,
                    "violations": result.violations,
                }
            )
        )
        if not result.passed:
            failed += 1

    if failed > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
