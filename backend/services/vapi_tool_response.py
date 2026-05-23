"""Format booking/availability tool results for conversational VAPI assistants."""

from __future__ import annotations

import json
from typing import Any, Dict, List

from backend.services.booking_service import check_day_availability_logic
from backend.services.tenant_resolver import TenantContext


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

    # Prefer slots near requested time (simple: move requested to front if exact match exists)
    if requested_time in available:
        ordered = [requested_time] + [s for s in available if s != requested_time]
    else:
        ordered = available
    return ordered[:max_slots]


def enrich_voice_availability_response(
    tenant: TenantContext,
    result: Dict[str, Any],
    *,
    date_iso: str,
    time_label: str,
) -> Dict[str, Any]:
    """
    Add fields the LLM uses for natural recovery when a slot is unavailable.
    """
    out = dict(result)
    out["requested_date"] = date_iso
    out["requested_time"] = time_label
    out["business_name"] = tenant.business_name

    if result.get("available") is True:
        out["voice_instruction"] = (
            f"The time {time_label} on {date_iso} is available for {tenant.business_name}. "
            "Confirm with the caller, then call book_appointment with their name and phone."
        )
        out["assistant_should_say"] = (
            f"That time is open on {date_iso}. May I book that for you?"
        )
        print(
            "[VAPI TOOL RESPONSE]",
            "check_availability",
            "available=true",
            f"date={date_iso!r}",
            f"time={time_label!r}",
        )
        return out

    # Unavailable — NOT a technical error unless availability_check_failed
    print(
        "[VAPI SLOT UNAVAILABLE]",
        f"business={tenant.business_name!r}",
        f"date={date_iso!r}",
        f"time={time_label!r}",
        f"calendar_check_failed={result.get('availability_check_failed')!r}",
        f"backend_message={result.get('message')!r}",
    )

    alts = _pick_alternative_slots(tenant, date_iso, time_label)
    out["slot_unavailable"] = True
    out["alternative_slots"] = alts

    if result.get("availability_check_failed"):
        out["voice_instruction"] = (
            "The live calendar could not be reached; schedule rules were used. "
            f"The requested slot is not available. Politely offer other times: "
            f"{', '.join(alts) if alts else 'another day or time'}. "
            "Do NOT say technical error unless the caller asks about system status."
        )
        out["assistant_should_say"] = (
            f"I'm sorry, {time_label} on {date_iso} isn't available. "
            + (
                f"Would {' or '.join(alts[:3])} work instead?"
                if alts
                else "Would another day or time work for you?"
            )
        )
    else:
        out["voice_instruction"] = (
            "The requested appointment time is NOT available. This is normal scheduling, NOT a technical failure. "
            f"Offer these open times on the same day: {', '.join(alts) if alts else 'none on this day — suggest another date'}. "
            "Ask which they prefer, call check_availability for their new choice, then book_appointment."
        )
        out["assistant_should_say"] = (
            f"That time is already booked. "
            + (
                f"I have {', '.join(alts[:4])} available on the same day — would any of those work?"
                if alts
                else f"Would you like a different day?"
            )
        )

    out["message"] = out.get("message") or "That slot is not available."
    print(
        "[VAPI TOOL RESPONSE]",
        "check_availability",
        "available=false",
        f"alternatives={alts!r}",
        f"voice_instruction_len={len(out.get('voice_instruction', ''))}",
    )
    return out


def enrich_voice_book_response(result: Dict[str, Any], tenant: TenantContext) -> Dict[str, Any]:
    out = dict(result)
    if result.get("status") == "confirmed":
        out["voice_instruction"] = (
            "Booking succeeded. Confirm the appointment details cheerfully with the caller."
        )
    else:
        out["voice_instruction"] = (
            "Booking did not complete. Apologize and offer to check availability for another time. "
            f"Reason: {result.get('message') or 'unknown'}. Do not mention internal errors."
        )
    print(
        "[VAPI TOOL RESPONSE]",
        "book_appointment",
        f"status={result.get('status')!r}",
        f"business={tenant.business_name!r}",
        f"preview={json.dumps(out, default=str)[:280]!r}",
    )
    return out
