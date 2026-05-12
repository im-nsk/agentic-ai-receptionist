"""Resolve the tenant's daily booking window from clients.working_hours JSON."""

from __future__ import annotations

import re
from typing import Any, Optional, Tuple

_DEFAULT_OPEN = 9 * 60
_DEFAULT_CLOSE = 18 * 60

_HH_MM = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")


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


def daily_booking_window_minutes(working_hours: Any) -> Tuple[int, int]:
    """
    Minutes from local midnight, half-open [open, close).
    Defaults 09:00–18:00 when missing or invalid.
    """
    if not isinstance(working_hours, dict):
        return _DEFAULT_OPEN, _DEFAULT_CLOSE
    win = working_hours.get("window")
    if not isinstance(win, dict):
        return _DEFAULT_OPEN, _DEFAULT_CLOSE
    open_m = _parse_hh_mm_to_minutes(str(win.get("start", "")))
    close_m = _parse_hh_mm_to_minutes(str(win.get("end", "")))
    if open_m is None or close_m is None or close_m <= open_m:
        return _DEFAULT_OPEN, _DEFAULT_CLOSE
    return open_m, close_m
