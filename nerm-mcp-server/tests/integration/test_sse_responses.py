from nerm.transports import TransportConfig


def test_sse_transport_path_is_supported() -> None:
    transport = TransportConfig(kind="streamable-http", host="0.0.0.0", port=8080)
    assert transport.kind == "streamable-http"
