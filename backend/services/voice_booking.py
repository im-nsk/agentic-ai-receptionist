"""Voice (VAPI) booking — same backend path as web, with explicit trace logs."""

from __future__ import annotations

import json
import traceback
import uuid
from typing import Any, Optional

from fastapi import BackgroundTasks, HTTPException
from sqlalchemy.orm import Session

from backend.services.booking_service import book_appointment_logic, check_availability_logic
from backend.services.tenant_resolver import TenantContext
from backend.services.vapi_tool_response import (
    enrich_voice_availability_response,
    enrich_voice_book_response,
    format_vapi_tool_result,
)
from backend.services.voice_datetime import VoiceDatetimeParseError, prepare_voice_booking_fields


def _log_voice_booking_started(tenant: TenantContext, *, tool_name: str, args: dict, call_id: str) -> None:
    print(
        "[VOICE BOOKING STARTED]",
        f"tool={tool_name!r}",
        f"call_id={call_id!r}",
        tenant.log_fields(),
        f"args={json.dumps(args, default=str)!r}",
    )


def _log_voice_booking_success(tenant: TenantContext, *, result: dict, call_id: str) -> None:
    print(
        "[VOICE BOOKING SUCCESS]",
        f"call_id={call_id!r}",
        tenant.log_fields(),
        f"calendar_id={tenant.calendar_id!r}",
        f"sheet_id={tenant.sheet_id!r}",
        f"result={json.dumps(result, default=str)!r}",
    )


def _log_voice_booking_failed(
    tenant: Optional[TenantContext],
    *,
    reason: str,
    call_id: str = "",
    exc: Optional[BaseException] = None,
) -> None:
    ctx = tenant.log_fields() if tenant else {}
    print(
        "[VOICE BOOKING FAILED]",
        f"call_id={call_id!r}",
        f"reason={reason!r}",
        f"tenant={ctx!r}",
    )
    if exc:
        traceback.print_exc()


def _voice_datetime_failure(
    tenant: TenantContext,
    exc: VoiceDatetimeParseError,
    *,
    call_id: str,
) -> dict:
    _log_voice_booking_failed(
        tenant,
        reason=f"date/time parse: {exc.reason or exc!s}",
        call_id=call_id,
        exc=exc,
    )
    return {
        "status": "failed",
        "available": False,
        "message": str(exc),
        "error": exc.reason or "invalid_date_or_time",
        "raw_date": exc.raw_date,
        "raw_time": exc.raw_time,
    }


def execute_voice_check_availability(
    db: Session,
    tenant: TenantContext,
    args: dict[str, Any],
    *,
    tool_name: str,
    call_id: str,
) -> dict:
    """Same as web availability check, after normalizing VAPI date/time strings."""
    raw_date = str(args.get("date") or args.get("appointment_date") or "").strip()
    raw_time = str(args.get("time") or args.get("appointment_time") or "").strip()
    if not raw_date or not raw_time:
        _log_voice_booking_failed(
            tenant,
            reason="missing date or time for availability check",
            call_id=call_id,
        )
        return {
            "available": False,
            "message": "date and time are required",
        }

    try:
        prepared = prepare_voice_booking_fields(args, tenant.timezone)
    except VoiceDatetimeParseError as exc:
        out = _voice_datetime_failure(tenant, exc, call_id=call_id)
        out.pop("status", None)
        return out

    date = prepared["date"]
    time = prepared["time"]

    print(
        "[VOICE AVAILABILITY CHECK]",
        f"tool={tool_name!r}",
        f"call_id={call_id!r}",
        tenant.log_fields(),
        f"date={date!r}",
        f"time={time!r}",
    )

    try:
        result = check_availability_logic(
            date=date,
            time=time,
            calendar_id=tenant.calendar_id,
            timezone_str=tenant.timezone,
            duration_minutes=tenant.slot_duration,
            weekly_availability=tenant.weekly_availability,
            blocked_dates=tenant.blocked_dates,
            working_hours=tenant.working_hours,
        )
        result = enrich_voice_availability_response(
            tenant,
            result,
            date_iso=date,
            time_label=time,
        )
        print(
            "[VOICE AVAILABILITY RESULT]",
            f"call_id={call_id!r}",
            f"available={result.get('available')}",
            f"message={result.get('message')!r}",
        )
        return result
    except Exception as exc:
        _log_voice_booking_failed(
            tenant,
            reason=f"availability check exception: {exc!r}",
            call_id=call_id,
            exc=exc,
        )
        return {
            "available": False,
            "not_a_system_error": True,
            "assistant_should_say": (
                "I had trouble checking that time. Could you tell me another day and time?"
            ),
            "message": "Availability check failed",
            "error": str(exc),
        }


def execute_voice_book(
    db: Session,
    tenant: TenantContext,
    args: dict[str, Any],
    background_tasks: BackgroundTasks,
    *,
    tool_name: str,
    call_id: str,
    default_caller_phone: str = "",
) -> dict:
    """
    Book using the same ``book_appointment_logic`` as POST /book-appointment (web).
    """
    _log_voice_booking_started(tenant, tool_name=tool_name, args=args, call_id=call_id)

    name = str(args.get("name") or args.get("customer_name") or "Phone caller").strip()
    phone = str(
        args.get("phone")
        or args.get("customer_phone")
        or args.get("caller_phone")
        or default_caller_phone
        or ""
    ).strip()
    raw_date = str(args.get("date") or args.get("appointment_date") or "").strip()
    raw_time = str(args.get("time") or args.get("appointment_time") or "").strip()
    notes = str(args.get("notes") or args.get("note") or "")[:4000]

    if not phone:
        _log_voice_booking_failed(
            tenant,
            reason="missing caller phone number",
            call_id=call_id,
        )
        return {"status": "failed", "message": "Customer phone number is required"}
    if not raw_date or not raw_time:
        _log_voice_booking_failed(
            tenant,
            reason="missing date or time",
            call_id=call_id,
        )
        return {"status": "failed", "message": "Appointment date and time are required"}

    if not tenant.calendar_id or not tenant.sheet_id:
        _log_voice_booking_failed(
            tenant,
            reason="tenant setup incomplete (calendar_id or sheet_id missing)",
            call_id=call_id,
        )
        return {
            "status": "failed",
            "message": "Business booking is not fully configured yet",
        }

    try:
        prepared = prepare_voice_booking_fields(args, tenant.timezone)
    except VoiceDatetimeParseError as exc:
        return _voice_datetime_failure(tenant, exc, call_id=call_id)

    date = prepared["date"]
    time = prepared["time"]

    try:
        result = book_appointment_logic(
            client_id=tenant.client_id,
            name=name,
            phone=phone,
            date=date,
            time=time,
            calendar_id=tenant.calendar_id,
            sheet_id=tenant.sheet_id,
            timezone_str=tenant.timezone,
            duration_minutes=tenant.slot_duration,
            background_tasks=background_tasks,
            db=db,
            source="vapi",
            notes=notes,
            weekly_availability=tenant.weekly_availability,
            blocked_dates=tenant.blocked_dates,
            working_hours=tenant.working_hours,
            business_name=tenant.business_name,
        )
        result = enrich_voice_book_response(
            result,
            tenant,
            date_iso=date,
            time_label=time,
        )
        if result.get("status") == "confirmed":
            _log_voice_booking_success(tenant, result=result, call_id=call_id)
        else:
            _log_voice_booking_failed(
                tenant,
                reason=result.get("message") or "create_event returned false",
                call_id=call_id,
            )
        return result
    except HTTPException as exc:
        _log_voice_booking_failed(
            tenant,
            reason=f"HTTP {exc.status_code}: {exc.detail}",
            call_id=call_id,
            exc=exc,
        )
        fail = enrich_voice_book_response(
            {"status": "failed", "message": str(exc.detail)},
            tenant,
            date_iso=date,
            time_label=time,
        )
        return fail
    except Exception as exc:
        _log_voice_booking_failed(
            tenant,
            reason=f"unexpected: {exc!r}",
            call_id=call_id,
            exc=exc,
        )
        return {"status": "failed", "message": "Booking failed", "error": str(exc)}
