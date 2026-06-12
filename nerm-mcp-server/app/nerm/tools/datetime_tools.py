from datetime import UTC, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def nerm_get_current_date_time(timezone: str | None = None) -> dict:
    """Return current date/time, optionally in a requested IANA timezone.

    Use this for time-aware reasoning (relative date math, "today", "now", windows).
    If `timezone` is omitted, UTC is returned by default.
    """
    timezone_name = (timezone or "UTC").strip() or "UTC"
    try:
        tzinfo = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        return {
            "error": "invalid_timezone",
            "status": 400,
            "message": f"Unknown timezone '{timezone_name}'. Use an IANA timezone such as 'UTC' or 'America/New_York'.",
        }

    now_local = datetime.now(tzinfo)
    now_utc = now_local.astimezone(UTC)
    return {
        "timezone": timezone_name,
        "current_datetime": now_local.isoformat(),
        "current_date": now_local.date().isoformat(),
        "current_time": now_local.time().replace(microsecond=0).isoformat(),
        "utc_datetime": now_utc.isoformat(),
        "unix_timestamp": int(now_utc.timestamp()),
    }
