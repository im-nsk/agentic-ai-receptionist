"""Shared booking + availability logic for web (/book-appointment) and VAPI."""

import uuid
from typing import Any, Optional

from fastapi import BackgroundTasks, HTTPException
from sqlalchemy.orm import Session

from backend.services.booking_datetime import BookingDatetimeError, assert_booking_start_in_future
from backend.services.calendar_service import check_availability, create_event, tenant_schedule_allows
from backend.services.phone_validation import normalize_and_validate_phone
from backend.services.sms_service import send_sms


def check_availability_logic(
    *,
    date: str,
    time: str,
    calendar_id: Optional[str],
    timezone_str: str,
    duration_minutes: int,
    weekly_availability: Optional[Any] = None,
    blocked_dates: Optional[Any] = None,
    working_hours: Optional[Any] = None,
) -> dict:
    duration_minutes = duration_minutes if duration_minutes > 0 else 30
    try:
        assert_booking_start_in_future(date, time, timezone_str)
    except BookingDatetimeError as exc:
        return {"available": False, "message": str(exc)}
    if not calendar_id:
        ok = tenant_schedule_allows(
            date,
            time,
            timezone_str,
            duration_minutes=duration_minutes,
            weekly_availability=weekly_availability,
            blocked_dates=blocked_dates,
            working_hours=working_hours,
        )
        return {
            "available": ok,
            "message": "Available" if ok else "Slot not available",
        }
    ok = check_availability(
        date,
        time,
        calendar_id=calendar_id,
        timezone=timezone_str,
        duration_minutes=duration_minutes,
        weekly_availability=weekly_availability,
        blocked_dates=blocked_dates,
        working_hours=working_hours,
    )
    return {"available": ok, "message": "Available" if ok else "Slot not available"}


def book_appointment_logic(
    *,
    client_id: uuid.UUID,
    name: str,
    phone: str,
    date: str,
    time: str,
    calendar_id: Optional[str],
    sheet_id: Optional[str],
    timezone_str: str,
    duration_minutes: int,
    background_tasks: BackgroundTasks,
    db: Session,
    source: str = "web",
    notes: str = "",
    weekly_availability: Optional[Any] = None,
    blocked_dates: Optional[Any] = None,
    working_hours: Optional[Any] = None,
    business_name: Optional[str] = None,
) -> dict:
    if not calendar_id or not sheet_id:
        raise HTTPException(status_code=400, detail="Client setup incomplete")

    try:
        phone = normalize_and_validate_phone(phone)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        assert_booking_start_in_future(date, time, timezone_str)
    except BookingDatetimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    duration_minutes = duration_minutes if duration_minutes > 0 else 30
    ok = create_event(
        name,
        phone,
        date,
        time,
        calendar_id=calendar_id,
        sheet_id=sheet_id,
        timezone=timezone_str,
        duration_minutes=duration_minutes,
        source=source,
        notes=notes,
        weekly_availability=weekly_availability,
        blocked_dates=blocked_dates,
        working_hours=working_hours,
        business_name=business_name,
    )

    if not ok:
        return {"status": "failed", "message": "Could not create booking"}

    background_tasks.add_task(
        send_sms,
        phone,
        f"Hi {name}, your appointment is confirmed on {date} at {time}",
    )

    return {"status": "confirmed", "message": "Booking confirmed"}
