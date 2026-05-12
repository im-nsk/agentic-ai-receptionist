"""Shared booking + availability logic for web (/book-appointment) and VAPI."""

import uuid
from typing import Optional

from fastapi import BackgroundTasks, HTTPException
from sqlalchemy.orm import Session

from backend.services.calendar_service import check_availability, create_event
from backend.services.sms_service import send_sms


def check_availability_logic(
    *,
    date: str,
    time: str,
    calendar_id: Optional[str],
    timezone_str: str,
    duration_minutes: int,
) -> dict:
    if not calendar_id:
        return {"available": False, "message": "Client setup incomplete"}
    duration_minutes = duration_minutes if duration_minutes > 0 else 30
    ok = check_availability(
        date,
        time,
        calendar_id=calendar_id,
        timezone=timezone_str,
        duration_minutes=duration_minutes,
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
) -> dict:
    if not calendar_id or not sheet_id:
        raise HTTPException(status_code=400, detail="Client setup incomplete")

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
    )

    if not ok:
        return {"status": "failed", "message": "Could not create booking"}

    background_tasks.add_task(
        send_sms,
        phone,
        f"Hi {name}, your appointment is confirmed on {date} at {time}",
    )

    return {"status": "confirmed", "message": "Booking confirmed"}
