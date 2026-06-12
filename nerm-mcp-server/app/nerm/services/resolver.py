def resolve_display_name(record: dict) -> str:
    return str(record.get("name") or record.get("display_name") or record.get("id") or "unknown")
