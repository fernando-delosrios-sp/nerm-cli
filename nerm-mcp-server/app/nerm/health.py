from nerm.server import build_server


def get_health_report() -> dict[str, object]:
    try:
        server = build_server()
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "error": str(exc)}
    return server.health()
