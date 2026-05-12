"""Aggregate booking metrics from Google Sheet row dicts (same shape as list_booking_rows_for_dashboard)."""

from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from zoneinfo import ZoneInfo


def _tz(name: str) -> ZoneInfo:
    n = (name or "").strip() or "America/New_York"
    try:
        return ZoneInfo(n)
    except Exception:
        return ZoneInfo("America/New_York")


def _safe_parse_date(value: Any) -> Optional[date]:
    if value is None:
        return None
    s = str(value).strip()
    if len(s) < 10:
        return None
    s10 = s[:10]
    if s10[4] != "-" or s10[7] != "-":
        return None
    try:
        y, m, d = int(s10[0:4]), int(s10[5:7]), int(s10[8:10])
        return date(y, m, d)
    except ValueError:
        return None


def _status_lower(value: Any) -> str:
    return str(value or "").strip().lower()


def _is_confirmed(status: str) -> bool:
    return status in ("confirmed", "booked")


def _is_cancelled(status: str) -> bool:
    return status in ("cancelled", "canceled")


def _iso_week_bounds(today: date) -> Tuple[date, date]:
    start = today - timedelta(days=today.weekday())
    end = start + timedelta(days=6)
    return start, end


def _last_7_calendar_dates(today: date) -> List[date]:
    return [today - timedelta(days=6 - i) for i in range(7)]


def compute_sheet_analytics(rows: List[Dict[str, Any]], timezone_str: str) -> Dict[str, Any]:
    """
    Pure aggregation — tolerates malformed date/status fields.
    Rolling "last 7 days" and "today" / "this week" use the tenant IANA timezone.
    """
    tz = _tz(timezone_str)
    now_local = datetime.now(tz)
    today = now_local.date()
    week_start, week_end = _iso_week_bounds(today)
    last7 = _last_7_calendar_dates(today)

    total = 0
    confirmed = 0
    cancelled = 0
    today_ct = 0
    week_ct = 0
    counts_by_day: List[int] = [0, 0, 0, 0, 0, 0, 0]
    labels: List[str] = [calendar.day_abbr[d.weekday()] for d in last7]

    for row in rows:
        if not isinstance(row, dict):
            continue
        total += 1
        st = _status_lower(row.get("status"))
        if _is_confirmed(st):
            confirmed += 1
        if _is_cancelled(st):
            cancelled += 1

        bd = _safe_parse_date(row.get("date"))
        if bd is not None:
            if bd == today:
                today_ct += 1
            if week_start <= bd <= week_end:
                week_ct += 1
            if _is_confirmed(st):
                try:
                    idx = last7.index(bd)
                    counts_by_day[idx] += 1
                except ValueError:
                    pass

    success_rate: Optional[float]
    if total <= 0:
        success_rate = None
    else:
        success_rate = round(100.0 * confirmed / total, 1)

    busiest: Optional[Dict[str, Any]] = None
    peak = max(counts_by_day) if counts_by_day else 0
    if peak > 0:
        idx = counts_by_day.index(peak)
        busiest = {"label": labels[idx], "count": peak}

    return {
        "source": "google_sheet",
        "timezone": (timezone_str or "").strip() or "America/New_York",
        "total_bookings": total,
        "confirmed_bookings": confirmed,
        "cancelled_bookings": cancelled,
        "bookings_today": today_ct,
        "bookings_this_week": week_ct,
        "success_rate_percent": success_rate,
        "busiest_day": busiest,
        "last_7_days_labels": labels,
        "last_7_days_confirmed_counts": counts_by_day,
    }


def empty_analytics_payload(
    *,
    integrations_ready: bool,
    rows_read_ok: bool,
    timezone_str: str,
) -> Dict[str, Any]:
    base = compute_sheet_analytics([], timezone_str)
    base["integrations_ready"] = integrations_ready
    base["rows_read_ok"] = rows_read_ok
    return base
