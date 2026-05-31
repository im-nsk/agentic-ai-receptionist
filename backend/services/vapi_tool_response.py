"""Format tool payloads for VAPI ``results[].result`` (single-line string the LLM reads)."""

from __future__ import annotations

import json
import re
from datetime import date as date_cls
from datetime import timedelta
from typing import Any, Dict, List, Optional

from backend.services.availability_rules import (
    candidate_slot_labels_12h_for_date,
    is_date_blocked,
    minutes_window_for_date,
    weekday_key_from_date_iso,
)
from backend.services.booking_service import (
    check_availability_logic,
    check_day_availability_logic,
)
from backend.services.tenant_resolver import TenantContext


def _single_line(text: str, *, max_len: int = 1200) -> str:
    """VAPI requires single-line tool results (no raw newlines)."""
    s = re.sub(r"\s+", " ", (text or "").strip())
    if len(s) > max_len:
        return s[: max_len - 3] + "..."
    return s


def _day_label(date_iso: str) -> str:
    try:
        return weekday_key_from_date_iso(date_iso).capitalize()
    except Exception:
        return date_iso


def _is_closed_day(tenant: TenantContext, date_iso: str) -> bool:
    if is_date_blocked(tenant.blocked_dates, date_iso):
        return True
    return minutes_window_for_date(
        tenant.weekly_availability,
        tenant.working_hours,
        date_iso,
    ) is None


def _pick_alternative_slots(
    tenant: TenantContext,
    date_iso: str,
    requested_time: str,
    *,
    max_slots: int = 6,
) -> List[str]:
    try:
        day = check_day_availability_logic(
            date=date_iso,
            calendar_id=tenant.calendar_id,
            timezone_str=tenant.timezone,
            duration_minutes=tenant.slot_duration,
            weekly_availability=tenant.weekly_availability,
            blocked_dates=tenant.blocked_dates,
            working_hours=tenant.working_hours,
        )
    except Exception as exc:
        print("[VAPI SLOT UNAVAILABLE]", f"day_lookup_failed={exc!r}")
        return []

    slots: Dict[str, bool] = day.get("slots") if isinstance(day.get("slots"), dict) else {}
    available = [label for label, ok in slots.items() if ok]
    if not available:
        return []
    if requested_time in available:
        ordered = [requested_time] + [s for s in available if s != requested_time]
    else:
        ordered = available
    return ordered[:max_slots]


def next_open_day_suggestions(
    tenant: TenantContext,
    from_date_iso: str,
    *,
    scan_days: int = 21,
    max_days: int = 3,
    slots_per_day: int = 4,
) -> List[Dict[str, Any]]:
    try:
        start = date_cls.fromisoformat(from_date_iso.strip())
    except ValueError:
        return []

    out: List[Dict[str, Any]] = []
    for offset in range(scan_days):
        cur = start + timedelta(days=offset)
        iso = cur.isoformat()
        if _is_closed_day(tenant, iso):
            continue
        times = candidate_slot_labels_12h_for_date(
            tenant.weekly_availability,
            tenant.working_hours,
            tenant.blocked_dates,
            iso,
            tenant.slot_duration,
        )[:slots_per_day]
        if not times:
            continue
        out.append({"date": iso, "day_name": _day_label(iso), "times": times})
        if len(out) >= max_days:
            break
    return out


def diagnose_schedule_rejection(
    tenant: TenantContext,
    date_iso: str,
    time_label: str,
) -> Dict[str, Any]:
    if is_date_blocked(tenant.blocked_dates, date_iso):
        return {
            "reason_code": "date_blocked",
            "reason": f"{date_iso} is blocked for bookings.",
        }
    if minutes_window_for_date(
        tenant.weekly_availability,
        tenant.working_hours,
        date_iso,
    ) is None:
        day = _day_label(date_iso)
        return {
            "reason_code": "closed_day",
            "reason": f"{tenant.business_name or 'We'} are closed on {day}s.",
            "day_name": day,
        }

    try:
        avail = check_availability_logic(
            date=date_iso,
            time=time_label,
            calendar_id=tenant.calendar_id,
            timezone_str=tenant.timezone,
            duration_minutes=tenant.slot_duration,
            weekly_availability=tenant.weekly_availability,
            blocked_dates=tenant.blocked_dates,
            working_hours=tenant.working_hours,
        )
    except Exception as exc:
        return {"reason_code": "check_error", "reason": str(exc)}

    if avail.get("available"):
        return {"reason_code": "unknown", "reason": "Slot appeared available but booking failed."}

    msg = str(avail.get("message") or "").strip()
    if "passed" in msg.lower():
        return {"reason_code": "past", "reason": msg}
    return {
        "reason_code": "slot_unavailable",
        "reason": msg or "That time is not available.",
    }


def _format_suggestions_phrase(suggestions: List[Dict[str, Any]]) -> str:
    if not suggestions:
        return "Please ask the caller for another day and time."
    parts = []
    for s in suggestions[:3]:
        times = ", ".join(s["times"][:3])
        parts.append(f"{s['day_name']} {s['date']} at {times}")
    return "You can offer: " + "; or ".join(parts) + "."


def build_unavailable_speech(
    tenant: TenantContext,
    date_iso: str,
    time_label: str,
    *,
    same_day_alts: Optional[List[str]] = None,
) -> Dict[str, Any]:
    diag = diagnose_schedule_rejection(tenant, date_iso, time_label)
    code = diag.get("reason_code", "")
    suggestions = next_open_day_suggestions(tenant, date_iso)
    same_day_alts = same_day_alts or []

    if code == "closed_day":
        day = diag.get("day_name") or _day_label(date_iso)
        offer = _format_suggestions_phrase(suggestions)
        say = (
            f"I'm sorry, {tenant.business_name or 'we'} aren't open on {day}s. "
            f"{offer.replace('You can offer: ', 'Would ')}"
        )
        instruction = (
            f"NORMAL SCHEDULING (not a technical error): closed on {day}. {offer} "
            "Ask which they prefer, call check_availability, then book_appointment."
        )
    elif same_day_alts:
        say = (
            f"That time on {date_iso} isn't available. "
            f"Same-day options include {', '.join(same_day_alts[:4])} — would any work?"
        )
        instruction = (
            "NORMAL SCHEDULING (not a technical error): offer same-day alternatives "
            f"{', '.join(same_day_alts[:6])}, then check_availability and book_appointment."
        )
    else:
        offer = _format_suggestions_phrase(suggestions)
        say = (
            f"I'm sorry, {time_label} on {date_iso} isn't available. "
            f"{offer.replace('You can offer: ', 'Would ')}"
        )
        instruction = f"NORMAL SCHEDULING (not a technical error). {offer}"

    return {
        "available": False,
        "slot_unavailable": True,
        "not_a_system_error": True,
        "reason_code": code,
        "reason": diag.get("reason"),
        "alternative_slots": same_day_alts,
        "next_open_days": suggestions,
        "assistant_should_say": say,
        "voice_instruction": instruction,
        "message": diag.get("reason") or "That time is not available.",
    }


def enrich_voice_availability_response(
    tenant: TenantContext,
    result: Dict[str, Any],
    *,
    date_iso: str,
    time_label: str,
) -> Dict[str, Any]:
    out = dict(result)
    out["requested_date"] = date_iso
    out["requested_time"] = time_label
    out["business_name"] = tenant.business_name
    out["not_a_system_error"] = True

    if result.get("available") is True:
        out["assistant_should_say"] = (
            f"Good news — {time_label} on {date_iso} is available. "
            "May I take your name and phone to book it?"
        )
        out["voice_instruction"] = "Slot available. Collect name and phone, then book_appointment."
        print("[VAPI TOOL RESPONSE]", "check_availability", "available=true")
        return out

    print(
        "[VAPI SLOT UNAVAILABLE]",
        f"business={tenant.business_name!r}",
        f"date={date_iso!r}",
        f"time={time_label!r}",
    )

    alts = _pick_alternative_slots(tenant, date_iso, time_label)
    enriched = build_unavailable_speech(tenant, date_iso, time_label, same_day_alts=alts)
    out.update(enriched)
    if result.get("availability_check_failed"):
        out["availability_check_failed"] = True
        out["voice_instruction"] = (
            str(out.get("voice_instruction") or "")
            + " Calendar sync was limited — still not a technical failure."
        )

    print(
        "[VAPI TOOL RESPONSE]",
        "check_availability",
        "available=false",
        f"reason_code={out.get('reason_code')!r}",
    )
    return out


def enrich_voice_book_response(
    result: Dict[str, Any],
    tenant: TenantContext,
    *,
    date_iso: str = "",
    time_label: str = "",
) -> Dict[str, Any]:
    out = dict(result)

    if result.get("status") == "confirmed":
        out["assistant_should_say"] = (
            f"You're all set — your appointment is confirmed for {time_label} on {date_iso}."
        )
        out["voice_instruction"] = "Booking succeeded. Confirm warmly with the caller."
        print("[VAPI TOOL RESPONSE]", "book_appointment", "status=confirmed")
        return out

    out["status"] = "not_booked"
    out["not_a_system_error"] = True

    if date_iso and time_label:
        alts = _pick_alternative_slots(tenant, date_iso, time_label)
        speech = build_unavailable_speech(tenant, date_iso, time_label, same_day_alts=alts)
        out.update(speech)
        out["voice_instruction"] = (
            "Booking not completed — this is NORMAL scheduling, NOT a system or technical error. "
            + str(speech.get("voice_instruction") or "")
        )
        out["message"] = speech.get("message") or result.get("message")
    else:
        out["assistant_should_say"] = (
            "I couldn't complete that booking. Would you like a different day or time?"
        )
        out["voice_instruction"] = "Not a technical error. Offer another time."

    print(
        "[VAPI TOOL RESPONSE]",
        "book_appointment",
        f"status=not_booked reason_code={out.get('reason_code')!r}",
    )
    return out


def format_vapi_tool_result(payload: Dict[str, Any], *, tool: str = "") -> str:
    """
    VAPI ``results[].result`` must be a single-line string (official server URL format).

    VAPI does not interpret ``voice_instruction`` separately — only this string is shown
    to the model. Lead with ``assistant_should_say``.
    """
    say = payload.get("assistant_should_say")
    if say:
        if payload.get("not_a_system_error"):
            return _single_line(f"SCHEDULING (not a system error): {say}")
        if payload.get("available") is True or payload.get("status") == "confirmed":
            return _single_line(f"SUCCESS: {say}")
        return _single_line(str(say))

    if payload.get("voice_instruction"):
        return _single_line(str(payload["voice_instruction"]))

    if payload.get("message"):
        return _single_line(str(payload["message"]))

    return _single_line(json.dumps(payload, default=str, separators=(",", ":")))
