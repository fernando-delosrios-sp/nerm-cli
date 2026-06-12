import pytest

from nerm.server import NermServer, build_server
from nerm.transports import TransportConfig


def test_server_run_delegates_to_fastmcp_app(monkeypatch) -> None:
    calls: list[str] = []

    class FakeFastMCP:
        def __init__(
            self,
            name: str,
            host: str,
            port: int,
            log_level: str,
            instructions: str | None = None,
        ) -> None:
            self.name = name

        def tool(self, name: str):  # noqa: ANN001
            def decorator(fn):  # noqa: ANN001
                return fn

            return decorator

        def run(self, transport: str = "stdio") -> None:
            calls.append(transport)

    monkeypatch.setattr("nerm.server.FastMCP", FakeFastMCP)
    server = build_server()
    server.run()
    assert calls == [server.transport.kind]


def test_server_run_raises_when_runtime_unavailable() -> None:
    server = NermServer(transport=TransportConfig(kind="stdio"), fastmcp_app=None)
    with pytest.raises(RuntimeError):
        server.run()
