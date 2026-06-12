from pathlib import Path
from typing import Callable
import logging

from nerm.config import get_settings
from nerm.logging import configure_logging
from nerm.tools.registry import NERM_TOOLS, register_tools
from nerm.transports import TransportConfig

try:
    from mcp.server.fastmcp import FastMCP  # type: ignore
except Exception:  # pragma: no cover
    FastMCP = None  # type: ignore


class NermServer:
    def __init__(self, transport: TransportConfig, fastmcp_app: object | None = None) -> None:
        self.transport = transport
        self._fastmcp_app = fastmcp_app
        self.tools: dict[str, Callable] = {}

    def run(self) -> None:
        if self._fastmcp_app is None:
            raise RuntimeError("FastMCP runtime is unavailable; cannot start MCP server loop.")
        run_fn = getattr(self._fastmcp_app, "run", None)
        if not callable(run_fn):
            raise RuntimeError("FastMCP app does not expose a callable run() method.")
        run_fn(transport=self.transport.kind)

    def health(self) -> dict[str, object]:
        return {
            "status": "ok",
            "transport": self.transport.kind,
            "host": self.transport.host,
            "port": self.transport.port,
            "tool_count": len(self.tools),
            "runtime_ready": self._fastmcp_app is not None,
        }


def _load_system_prompt() -> str | None:
    prompt_path = Path(__file__).resolve().parents[1] / "Agent" / "system_prompt.txt"
    if not prompt_path.exists():
        logging.getLogger("nerm.server").warning("system prompt file not found at %s", prompt_path)
        return None
    content = prompt_path.read_text(encoding="utf-8").strip()
    return content or None


def _validate_startup_settings(settings: object) -> None:
    api_base_path = str(getattr(settings, "nerm_api_base_path", "")).strip()
    if not api_base_path:
        raise ValueError("NERM_API_BASE_PATH must not be empty.")
    if not api_base_path.startswith("/"):
        raise ValueError("NERM_API_BASE_PATH must start with '/'.")


def build_server() -> NermServer:
    settings = get_settings()
    configure_logging(settings.log_level)
    _validate_startup_settings(settings)
    transport = TransportConfig(kind=settings.nerm_transport, host=settings.nerm_http_host, port=settings.nerm_http_port)
    app = None
    if FastMCP is not None:
        instructions = _load_system_prompt()
        app = FastMCP(
            "nerm-agent",
            instructions=instructions,
            host=settings.nerm_http_host,
            port=settings.nerm_http_port,
            log_level=settings.log_level.upper(),
        )
        for name, fn in NERM_TOOLS.items():
            app.tool(name=name)(fn)
    server = NermServer(transport=transport, fastmcp_app=app)
    register_tools(server)
    return server


def build_fastmcp() -> object:
    if FastMCP is None:
        return build_server()
    app = FastMCP("nerm-agent", instructions=_load_system_prompt())
    for name, fn in NERM_TOOLS.items():
        app.tool(name=name)(fn)
    return app
