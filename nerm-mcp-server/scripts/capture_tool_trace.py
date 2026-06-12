from __future__ import annotations

import argparse
import json
from pathlib import Path

from nerm.evals.trace_capture import build_trace_payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert nerm-agent log lines into eval trace JSON (calls + final_response)."
    )
    parser.add_argument("--log-file", required=True, help="Path to captured server/client log text file.")
    parser.add_argument("--out", required=True, help="Output trace JSON path.")
    parser.add_argument(
        "--final-response-file",
        required=False,
        help="Optional path to plaintext final response captured from the agent run.",
    )
    args = parser.parse_args()

    log_path = Path(args.log_file).resolve()
    out_path = Path(args.out).resolve()
    final_response = ""
    if args.final_response_file:
        final_response = Path(args.final_response_file).resolve().read_text(encoding="utf-8")

    lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    payload = build_trace_payload(lines, final_response=final_response)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(json.dumps({"trace_path": str(out_path), "call_count": len(payload.get("calls", []))}))


if __name__ == "__main__":
    main()
