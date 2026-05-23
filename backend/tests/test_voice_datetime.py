"""Voice date/time normalization (no DB)."""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from backend.services.voice_datetime import (
    VoiceDatetimeParseError,
    normalize_voice_booking_datetime,
)


def test_iso_date_unchanged():
    d, t = normalize_voice_booking_datetime("2030-05-25", "10:00 AM", "America/New_York")
    assert d == "2030-05-25"
    assert "10:00" in t


def test_ordinal_day_only_uses_current_or_next_month():
    tz = ZoneInfo("America/New_York")
    now = datetime.now(tz)
    d, _t = normalize_voice_booking_datetime("25th", "11:59 PM", "America/New_York")
    assert d.startswith(f"{now.year}-")
    parts = d.split("-")
    assert int(parts[2]) == 25


def test_tomorrow():
    from datetime import timedelta

    tz = ZoneInfo("America/New_York")
    now = datetime.now(tz)
    tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d")
    d, _ = normalize_voice_booking_datetime("tomorrow", "9:00 AM", "America/New_York")
    assert d == tomorrow


def test_may_25th():
    d, t = normalize_voice_booking_datetime("May 25th, 2030", "3:30 PM", "America/New_York")
    assert d == "2030-05-25"
    assert "3:30" in t


def test_invalid_date_raises():
    with pytest.raises(VoiceDatetimeParseError) as exc:
        normalize_voice_booking_datetime("not-a-date", "10:00 AM", "America/New_York")
    assert exc.value.reason


def test_24h_time_normalized_to_12h():
    _d, t = normalize_voice_booking_datetime("2030-06-01", "14:00", "America/New_York")
    assert "PM" in t or "2:00" in t
