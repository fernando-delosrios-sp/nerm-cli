import pytest

from nerm.config import get_settings
from nerm.server import build_server
from nerm.transports import TransportConfig


def test_stdio_transport_default() -> None:
    server = build_server()
    assert server.transport.kind == "stdio"


def test_stdio_transport_validates_port() -> None:
    with pytest.raises(ValueError):
        TransportConfig(kind="stdio", port=70000)


def test_build_server_rejects_invalid_transport_kind_from_env(monkeypatch) -> None:
    monkeypatch.setenv("NERM_TRANSPORT", "invalid-kind")
    get_settings.cache_clear()
    with pytest.raises(ValueError):
        build_server()
    get_settings.cache_clear()
