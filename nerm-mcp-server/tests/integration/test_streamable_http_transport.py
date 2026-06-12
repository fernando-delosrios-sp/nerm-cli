import pytest

from nerm.config import Settings
from nerm.config import get_settings
from nerm.server import build_server
from nerm.transports import TransportConfig


def test_streamable_http_transport_object() -> None:
    settings = Settings(NERM_TRANSPORT="streamable-http")
    transport = TransportConfig(kind=settings.nerm_transport, host=settings.nerm_http_host, port=settings.nerm_http_port)
    assert transport.kind == "streamable-http"


def test_invalid_transport_kind_rejected() -> None:
    with pytest.raises(ValueError):
        TransportConfig(kind="invalid", host="0.0.0.0", port=8080)  # type: ignore[arg-type]


def test_invalid_transport_port_rejected() -> None:
    with pytest.raises(ValueError):
        TransportConfig(kind="streamable-http", host="0.0.0.0", port=0)


def test_build_server_rejects_invalid_transport_port_from_env(monkeypatch) -> None:
    monkeypatch.setenv("NERM_TRANSPORT", "streamable-http")
    monkeypatch.setenv("NERM_HTTP_PORT", "70000")
    get_settings.cache_clear()
    with pytest.raises(ValueError):
        build_server()
    get_settings.cache_clear()
