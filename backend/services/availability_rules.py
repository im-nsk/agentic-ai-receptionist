"""Structured weekly availability, blocked dates, and legacy working_hours.window fallback."""

from __future__ import annotations

import re
from datetime import date as date_cls
from typing import Any, Dict, Optional, Set, Tuple

from backend.services.booking_window import daily_booking_window_minutes

DAY_KEYS: Tuple[str, ...] = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)

_HH_MM = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")
_DATE_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _parse_hh_mm_to_minutes(raw: str) -> Optional[int]:
    s = (raw or "").strip()
    if not s:
        return None
    m = _HH_MM.match(s)
    if not m:
        return None
    h = int(m.group(1))
    mm = int(m.group(2))
    if h < 0 or h > 23 or mm < 0 or mm > 59:
        return None
    return h * 60 + mm


def _minutes_to_hhmm(total: int) -> str:
    t = ((total % (24 * 60)) + 24 * 60) % (24 * 60)
    h = t // 60
    mm = t % 60
    return f"{h:02d}:{mm:02d}"


def weekday_key_from_date_iso(date_iso: str) -> str:
    d = date_cls.fromisoformat(date_iso.strip())
    return DAY_KEYS[d.weekday()]


def is_date_blocked(blocked_dates: Any, date_iso: str) -> bool:
    if not isinstance(blocked_dates, list):
        return False
    needle = date_iso.strip()
    for x in blocked_dates:
        if str(x).strip() == needle:
            return True
    return False


def _is_complete_weekly(weekly: Any) -> bool:
    if not isinstance(weekly, dict):
        return False
    for k in DAY_KEYS:
        if k not in weekly or not isinstance(weekly[k], dict):
            return False
    return True


def weekly_from_legacy_working_hours(working_hours: Any) -> Dict[str, Dict[str, Any]]:
    """All days share the same window (matches old single-window behavior)."""
    open_m, close_m = daily_booking_window_minutes(working_hours)
    start = _minutes_to_hhmm(open_m)
    end = _minutes_to_hhmm(close_m)
    return {k: {"enabled": True, "start": start, "end": end} for k in DAY_KEYS}


def default_weekly_availability() -> Dict[str, Dict[str, Any]]:
    """Mon–Fri 09:00–17:00; Sat–Sun closed (sensible SaaS default)."""
    out: Dict[str, Dict[str, Any]] = {}
    for k in DAY_KEYS:
        if k in ("saturday", "sunday"):
            out[k] = {"enabled": False, "start": "09:00", "end": "17:00"}
        else:
            out[k] = {"enabled": True, "start": "09:00", "end": "17:00"}
    return out


def effective_weekly_availability(weekly_availability: Any, working_hours: Any) -> Dict[str, Dict[str, Any]]:
    if _is_complete_weekly(weekly_availability):
        return normalize_weekly_availability(weekly_availability)
    if isinstance(working_hours, dict) and working_hours.get("window"):
        return weekly_from_legacy_working_hours(working_hours)
    return default_weekly_availability()


def _coerce_bool(value: Any, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        s = value.strip().lower()
        if s in ("true", "1", "yes", "on"):
            return True
        if s in ("false", "0", "no", "off"):
            return False
    return bool(value)


def _day_enabled(seg: Dict[str, Any]) -> bool:
    """Accept legacy `open` or `enabled` keys from settings payloads."""
    if "enabled" in seg:
        return _coerce_bool(seg.get("enabled"), True)
    if "open" in seg:
        return _coerce_bool(seg.get("open"), True)
    return True


def normalize_weekly_availability(raw: Any) -> Dict[str, Dict[str, Any]]:
    """Ensure all seven keys with enabled + start + end strings."""
    src = raw if isinstance(raw, dict) else {}
    out: Dict[str, Dict[str, Any]] = {}
    for k in DAY_KEYS:
        seg = src.get(k)
        if not isinstance(seg, dict):
            seg = {}
        enabled = _day_enabled(seg)
        start = str(seg.get("start", "09:00")).strip() or "09:00"
        end = str(seg.get("end", "17:00")).strip() or "17:00"
        out[k] = {"enabled": enabled, "start": start, "end": end}
    return out


def minutes_window_for_date(
    weekly_availability: Any,
    working_hours: Any,
    date_iso: str,
) -> Optional[Tuple[int, int]]:
    """Minutes from midnight for that calendar date, or None if closed / invalid."""
    eff = effective_weekly_availability(weekly_availability, working_hours)
    key = weekday_key_from_date_iso(date_iso)
    day = eff.get(key) or {}
    if not day.get("enabled"):
        return None
    sm = _parse_hh_mm_to_minutes(str(day.get("start", "")))
    em = _parse_hh_mm_to_minutes(str(day.get("end", "")))
    if sm is None or em is None or em <= sm:
        return None
    return sm, em


def candidate_slot_times_for_date(
    weekly_availability: Any,
    working_hours: Any,
    blocked_dates: Any,
    date_iso: str,
    duration_minutes: int,
) -> list[str]:
    """HH:MM labels on the booking grid for a day (before calendar filtering)."""
    if is_date_blocked(blocked_dates, date_iso):
        return []
    win = minutes_window_for_date(weekly_availability, working_hours, date_iso)
    if win is None:
        return []
    open_m, close_m = win
    dur = max(1, int(duration_minutes) if duration_minutes else 30)
    return [_minutes_to_hhmm(m) for m in range(open_m, close_m, dur)]


def is_slot_on_duration_grid(mins: int, open_mins: int, duration_minutes: int) -> bool:
    """Slot start aligns with duration steps from the day's open time (not midnight)."""
    dur = max(1, int(duration_minutes) if duration_minutes else 30)
    if mins < open_mins:
        return False
    return (mins - open_mins) % dur == 0


def normalize_blocked_dates(raw: Any, *, max_items: int = 200) -> list[str]:
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    seen: Set[str] = set()
    for x in raw:
        s = str(x).strip()
        if not _DATE_ISO.match(s) or s in seen:
            continue
        seen.add(s)
        out.append(s)
        if len(out) >= max_items:
            break
    out.sort()
    return out


def validate_weekly_availability_dict(raw: Any) -> Dict[str, Any]:
    """Raises ValueError if invalid."""
    if not isinstance(raw, dict):
        raise ValueError("weekly_availability must be an object")
    norm = normalize_weekly_availability(raw)
    for k in DAY_KEYS:
        day = norm[k]
        if not day["enabled"]:
            continue
        sm = _parse_hh_mm_to_minutes(day["start"])
        em = _parse_hh_mm_to_minutes(day["end"])
        if sm is None or em is None or em <= sm:
            raise ValueError(f"Invalid hours for {k}")
    return norm
