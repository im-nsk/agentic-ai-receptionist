"""Normalize natural-language dates/times from VAPI tool arguments before shared booking logic."""

from __future__ import annotations

import json
import re
from datetime import date as date_cls
from datetime import datetime, timedelta
from typing import Any, Dict, Tuple

from dateutil import parser as dateutil_parser
from dateutil.relativedelta import relativedelta
from zoneinfo import ZoneInfo

from backend.services.availability_rules import _minutes_to_12h_label
from backend.services.booking_datetime import BookingDatetimeError, assert_booking_start_in_future

_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_ORDINAL_DAY_ONLY_RE = re.compile(r"^(\d{1,2})\s*(st|nd|rd|th)?\.?$", re.IGNORECASE)
_HH_MM_RE = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")


class VoiceDatetimeParseError(ValueError):
    """Voice tool sent a date/time the booking pipeline cannot use."""

    def __init__(
        self,
        message: str,
        *,
        raw_date: str = "",
        raw_time: str = "",
        reason: str = "",
    ):
        super().__init__(message)
        self.raw_date = raw_date
        self.raw_time = raw_time
        self.reason = reason or message


def _tenant_now(timezone_str: str) -> tuple[ZoneInfo, datetime]:
    tz_name = (timezone_str or "").strip() or "America/New_York"
    tz = ZoneInfo(tz_name)
    return tz, datetime.now(tz)


def _normalize_date_iso(date_raw: str, now: datetime, tz: ZoneInfo) -> str:
    s = (date_raw or "").strip()
    if not s:
        raise VoiceDatetimeParseError(
            "Appointment date is required.",
            raw_date=date_raw,
            reason="empty_date",
        )

    if _ISO_DATE_RE.match(s):
        try:
            date_cls.fromisoformat(s)
        except ValueError as exc:
            raise VoiceDatetimeParseError(
                f"Invalid calendar date: {s!r}",
                raw_date=date_raw,
                reason="invalid_iso_date",
            ) from exc
        return s

    lower = s.lower().strip()
    if lower in ("today",):
        return now.strftime("%Y-%m-%d")
    if lower in ("tomorrow",):
        return (now + timedelta(days=1)).strftime("%Y-%m-%d")

    ord_m = _ORDINAL_DAY_ONLY_RE.match(s)
    if ord_m:
        day = int(ord_m.group(1))
        if day < 1 or day > 31:
            raise VoiceDatetimeParseError(
                f"Invalid day of month: {day}",
                raw_date=date_raw,
                reason="ordinal_out_of_range",
            )
        try:
            candidate = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            candidate = candidate + relativedelta(day=day)
        except ValueError as exc:
            raise VoiceDatetimeParseError(
                f"Could not build a date from day {day}",
                raw_date=date_raw,
                reason="ordinal_invalid_for_month",
            ) from exc
        if candidate.date() < now.date():
            candidate = candidate + relativedelta(months=1)
        return candidate.strftime("%Y-%m-%d")

    try:
        dt = dateutil_parser.parse(s, default=now, fuzzy=True)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tz)
        else:
            dt = dt.astimezone(tz)
        return dt.strftime("%Y-%m-%d")
    except Exception as exc:
        raise VoiceDatetimeParseError(
            f"Could not understand the appointment date {date_raw!r}. "
            "Please use YYYY-MM-DD or a full date like May 25th.",
            raw_date=date_raw,
            reason=f"dateutil_parse_failed:{exc!r}",
        ) from exc


def _normalize_time_label(
    time_raw: str,
    date_iso: str,
    tz: ZoneInfo,
) -> str:
    s = (time_raw or "").strip()
    if not s:
        raise VoiceDatetimeParseError(
            "Appointment time is required.",
            raw_time=time_raw,
            reason="empty_time",
        )

    hhmm = _HH_MM_RE.match(s)
    if hhmm:
        h = int(hhmm.group(1))
        m = int(hhmm.group(2))
        return _minutes_to_12h_label(h * 60 + m)

    y, mo, d = (int(x) for x in date_iso.split("-"))
    day_start = datetime(y, mo, d, 9, 0, tzinfo=tz)

    try:
        dt = dateutil_parser.parse(s, default=day_start, fuzzy=True)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tz)
        else:
            dt = dt.astimezone(tz)
        return _minutes_to_12h_label(dt.hour * 60 + dt.minute)
    except Exception as exc:
        raise VoiceDatetimeParseError(
            f"Could not understand the appointment time {time_raw!r}. "
            "Please use a time like 2:30 PM.",
            raw_time=time_raw,
            reason=f"time_parse_failed:{exc!r}",
        ) from exc


def normalize_voice_booking_datetime(
    raw_date: str,
    raw_time: str,
    timezone_str: str,
) -> Tuple[str, str]:
    """
    Convert VAPI/LLM date/time strings to formats used by web booking.

    Returns:
        (date_iso ``YYYY-MM-DD``, time label e.g. ``10:00 AM``)
    """
    tz, now = _tenant_now(timezone_str)
    date_raw_s = (raw_date or "").strip()
    time_raw_s = (raw_time or "").strip()

    print(
        "[VOICE DATE RAW]",
        f"date={date_raw_s!r}",
        f"time={time_raw_s!r}",
        f"timezone={tz.key!r}",
    )

    date_iso = _normalize_date_iso(date_raw_s, now, tz)
    time_label = _normalize_time_label(time_raw_s, date_iso, tz)

    print(
        "[VOICE DATE NORMALIZED]",
        f"date={date_iso!r}",
        f"time={time_label!r}",
    )

    try:
        assert_booking_start_in_future(date_iso, time_label, tz.key)
    except BookingDatetimeError as exc:
        raise VoiceDatetimeParseError(
            str(exc),
            raw_date=date_raw_s,
            raw_time=time_raw_s,
            reason="not_in_future",
        ) from exc

    print(
        "[VOICE BOOKING VALIDATION]",
        "passed (same assert_booking_start_in_future as web)",
    )

    return date_iso, time_label


def prepare_voice_booking_fields(
    args: Dict[str, Any],
    timezone_str: str,
) -> Dict[str, Any]:
    """
    Copy tool args with normalized ``date`` / ``time`` keys for booking_service.
    Raises VoiceDatetimeParseError when normalization fails.
    """
    raw_date = str(args.get("date") or args.get("appointment_date") or "").strip()
    raw_time = str(args.get("time") or args.get("appointment_time") or "").strip()

    date_iso, time_label = normalize_voice_booking_datetime(
        raw_date,
        raw_time,
        timezone_str,
    )

    prepared = dict(args)
    prepared["date"] = date_iso
    prepared["time"] = time_label
    prepared["_voice_date_raw"] = raw_date
    prepared["_voice_time_raw"] = raw_time

    print(
        "[VOICE BOOKING PAYLOAD]",
        json.dumps(
            {
                "date": date_iso,
                "time": time_label,
                "name": prepared.get("name") or prepared.get("customer_name"),
                "phone": prepared.get("phone") or prepared.get("customer_phone"),
            },
            default=str,
        ),
    )

    return prepared


# Recommended VAPI custom-tool parameter descriptions (dashboard / OpenAPI).
VAPI_TOOL_DATE_PARAM_HINT = (
    "Required. Calendar date in YYYY-MM-DD format (example: 2026-05-25). "
    "Do not pass ordinals alone like '25th' — include month and year."
)
VAPI_TOOL_TIME_PARAM_HINT = (
    "Required. Time in 12-hour form (example: 2:30 PM) or 24-hour HH:MM."
)
