from __future__ import annotations

import json
from pathlib import Path

import anyio
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from nerm.test_agent import suggest_tool_call


def _print_help() -> None:
    print(
        "\nCommands:\n"
        "  /help                      Show help\n"
        "  /tools                     List available tools\n"
        "  /call <tool> <json>        Call tool with JSON args\n"
        "  /quit                      Exit\n"
        "Natural language input will attempt a heuristic tool suggestion.\n"
    )


def _parse_call_command(raw: str) -> tuple[str, dict[str, object]] | None:
    prefix = "/call "
    if not raw.startswith(prefix):
        return None
    rest = raw[len(prefix) :].strip()
    if " " not in rest:
        return None
    name, json_blob = rest.split(" ", 1)
    args = json.loads(json_blob)
    if not isinstance(args, dict):
        raise ValueError("JSON arguments must be an object")
    return name.strip(), args


async def _run_chat() -> None:
    params = StdioServerParameters(
        command="python",
        args=["-m", "main"],
        cwd=Path(__file__).resolve().parents[1],
        env={"PYTHONPATH": str(Path(__file__).resolve().parents[1] / "app")},
    )
    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            _ = await session.initialize()
            print("Connected to nerm-agent MCP server.")
            _print_help()
            while True:
                raw = await anyio.to_thread.run_sync(lambda: input("agent> ").strip())
                if not raw:
                    continue
                if raw == "/quit":
                    print("Bye.")
                    return
                if raw == "/help":
                    _print_help()
                    continue
                if raw == "/tools":
                    tools = await session.list_tools()
                    names = [t.name for t in tools.tools]
                    print(json.dumps({"tools": names}, indent=2))
                    continue
                if raw.startswith("/call "):
                    try:
                        parsed = _parse_call_command(raw)
                        if parsed is None:
                            print("Usage: /call <tool_name> <json_args>")
                            continue
                        tool_name, args = parsed
                        result = await session.call_tool(tool_name, args)
                        print(json.dumps(result.model_dump(exclude_none=True), indent=2, default=str))
                    except Exception as exc:  # noqa: BLE001
                        print(f"error: {exc}")
                    continue

                suggestion = suggest_tool_call(raw)
                if suggestion is None:
                    print("No heuristic mapping found. Use /tools then /call.")
                    continue
                print(f"heuristic -> {suggestion.name} {json.dumps(suggestion.arguments)}")
                try:
                    result = await session.call_tool(suggestion.name, suggestion.arguments)
                    print(json.dumps(result.model_dump(exclude_none=True), indent=2, default=str))
                except Exception as exc:  # noqa: BLE001
                    print(f"error: {exc}")


def main() -> None:
    anyio.run(_run_chat)


if __name__ == "__main__":
    main()
