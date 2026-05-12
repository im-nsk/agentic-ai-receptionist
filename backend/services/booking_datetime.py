"""Booking instant validation in the tenant (client) timezone."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from backend.services.calendar_service import parse_datetime


class BookingDatetimeError(ValueError):
    """Invalid or non-future booking start."""


def assert_booking_start_in_future(date: str, time: str, timezone_str: str) -> None:
    """Reject booking starts at or before 'now' (UTC comparison of instants). Uses client.timezone for parsing."""
    tz_name = (timezone_str or "").strip() or "America/New_York"
    try:
        booking_dt = parse_datetime(date.strip(), time.strip(), tz_name)
    except Exception as exc:
        raise BookingDatetimeError("Invalid date or time.") from exc
    start_utc = booking_dt.astimezone(ZoneInfo("UTC"))
    if start_utc <= datetime.now(ZoneInfo("UTC")):
        raise BookingDatetimeError("That time has already passed for your business timezone.")
