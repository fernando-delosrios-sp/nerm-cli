from datetime import datetime

from nerm.tools.datetime_tools import nerm_get_current_date_time


def test_get_current_date_time_defaults_to_utc() -> None:
    result = nerm_get_current_date_time()
    assert result["timezone"] == "UTC"
    assert isinstance(result["unix_timestamp"], int)
    assert "error" not in result
    parsed = datetime.fromisoformat(result["current_datetime"])
    assert parsed.tzinfo is not None


def test_get_current_date_time_accepts_timezone() -> None:
    result = nerm_get_current_date_time("America/New_York")
    assert result["timezone"] == "America/New_York"
    assert isinstance(result["unix_timestamp"], int)
    assert "error" not in result
    parsed = datetime.fromisoformat(result["current_datetime"])
    assert parsed.tzinfo is not None


def test_get_current_date_time_rejects_unknown_timezone() -> None:
    result = nerm_get_current_date_time("Mars/Phobos")
    assert result["error"] == "invalid_timezone"
    assert result["status"] == 400
