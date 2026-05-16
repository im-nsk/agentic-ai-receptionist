import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dateutil import parser

from backend.services.google_errors import google_http_error_message, google_http_status
from backend.services.availability_rules import (
    is_date_blocked,
    minutes_window_for_date,
)
from backend.services.human_booking_id import generate_human_booking_id
from backend.services.sheets_service import save_to_sheet


# ---------------- GOOGLE CREDENTIALS ---------------- #
SCOPES = ['https://www.googleapis.com/auth/calendar']

credentials_info = json.loads(os.getenv("GOOGLE_CREDENTIALS_JSON"))

credentials = service_account.Credentials.from_service_account_info(
    credentials_info,
    scopes=SCOPES
)

service = build('calendar', 'v3', credentials=credentials)


class CalendarAccessNotGrantedError(Exception):
    """Raised when the service account cannot read the tenant calendar (not shared, wrong ID, etc.)."""


def verify_tenant_calendar_readable(calendar_id: str) -> None:
    """
    Confirms the service account can read events on the tenant calendar (same API as booking).
    Accepts the owner's email as calendar ID (e.g. user@gmail.com). Does not use "primary".
  """
    cal = (calendar_id or "").strip()
    if not cal:
        raise CalendarAccessNotGrantedError("Calendar ID is required.")
    if cal.lower() == "primary":
        raise CalendarAccessNotGrantedError(
            'Use your Google account email as the Calendar ID (e.g. you@gmail.com), not "primary".'
        )

    now = datetime.now(timezone.utc)
    time_min = now.isoformat()
    time_max = (now + timedelta(days=1)).isoformat()

    try:
        service.events().list(
            calendarId=cal,
            timeMin=time_min,
            timeMax=time_max,
            maxResults=1,
            singleEvents=True,
        ).execute()
    except HttpError as e:
        code = google_http_status(e)
        api_msg = google_http_error_message(e)
        print(
            "SETUP calendar HttpError:",
            f"status={code}",
            f"calendar_id={cal!r}",
            f"api_message={api_msg!r}",
            f"body={e.content!r}",
        )
        if code in (403, 404):
            raise CalendarAccessNotGrantedError(
                f"Cannot read Google Calendar {cal!r}: {api_msg} (HTTP {code}). "
                "Use your Google account email as the Calendar ID and share that calendar with the "
                "booking service account (at least See all event details)."
            ) from e
        raise CalendarAccessNotGrantedError(
            f"Google Calendar API error for {cal!r}: {api_msg} (HTTP {code})."
        ) from e
    except Exception as e:
        print("SETUP calendar verify unexpected:", repr(e), f"calendar_id={cal!r}")
        raise RuntimeError(f"Calendar verification failed: {e!r}") from e


# ---------------- PARSER ---------------- #

def parse_datetime(date, time, timezone):
    try:
        dt = parser.parse(f"{date} {time}", fuzzy=True)
        tz = ZoneInfo(timezone)
        return dt.replace(tzinfo=tz)

    except Exception:
        raise ValueError(f"Invalid date/time input: {date} {time}")


# ---------------- VALIDATIONS ---------------- #

def is_valid_slot(dt, duration_minutes: int = 30):
    duration_minutes = duration_minutes or 30
    mins = dt.hour * 60 + dt.minute
    return mins % duration_minutes == 0 and dt.second == 0


def is_within_booking_window(dt, open_mins: int, close_mins: int) -> bool:
    """Half-open [open_mins, close_mins) in the booking timezone wall clock."""
    mins = dt.hour * 60 + dt.minute
    return open_mins <= mins < close_mins


def _tenant_rules_ok(
    booking_dt,
    date_str: str,
    duration_minutes: int,
    weekly_availability: Optional[Any],
    blocked_dates: Optional[Any],
    working_hours: Optional[Any],
) -> bool:
    if is_date_blocked(blocked_dates, date_str):
        return False
    win = minutes_window_for_date(weekly_availability, working_hours, date_str)
    if win is None:
        return False
    open_m, close_m = win
    if not is_valid_slot(booking_dt, duration_minutes):
        return False
    if not is_within_booking_window(booking_dt, open_m, close_m):
        return False
    return True


def tenant_schedule_allows(
    date,
    time,
    timezone,
    duration_minutes: int = 30,
    weekly_availability: Optional[Any] = None,
    blocked_dates: Optional[Any] = None,
    working_hours: Optional[Any] = None,
) -> bool:
    """Blocked dates + weekly hours + slot grid (no Google Calendar)."""
    try:
        booking_dt = parse_datetime(date, time, timezone)
    except Exception:
        return False
    duration_minutes = duration_minutes or 30
    start_time = booking_dt.astimezone(ZoneInfo("UTC"))
    if start_time <= datetime.now(ZoneInfo("UTC")):
        return False
    return _tenant_rules_ok(
        booking_dt,
        str(date).strip(),
        duration_minutes,
        weekly_availability,
        blocked_dates,
        working_hours,
    )


# ---------------- CHECK AVAILABILITY ---------------- #

def check_availability(
    date,
    time,
    calendar_id,
    timezone,
    duration_minutes: int = 30,
    weekly_availability: Optional[Any] = None,
    blocked_dates: Optional[Any] = None,
    working_hours: Optional[Any] = None,
):

    try:
        booking_dt = parse_datetime(date, time, timezone)
    except Exception:
        return False

    # ❌ Missing config safety
    if not calendar_id:
        return False

    duration_minutes = duration_minutes or 30

    start_time = booking_dt.astimezone(ZoneInfo("UTC"))
    end_time = start_time + timedelta(minutes=duration_minutes)

    # Past
    if start_time <= datetime.now(ZoneInfo("UTC")):
        return False

    if not _tenant_rules_ok(
        booking_dt,
        str(date).strip(),
        duration_minutes,
        weekly_availability,
        blocked_dates,
        working_hours,
    ):
        return False

    # Google Calendar conflicts
    events = service.events().list(
        calendarId=calendar_id,
        timeMin=start_time.isoformat(),
        timeMax=end_time.isoformat()
    ).execute()

    return len(events.get('items', [])) == 0


# ---------------- CREATE EVENT ---------------- #

def create_event(
    name,
    phone,
    date,
    time,
    calendar_id,
    sheet_id,
    timezone,
    duration_minutes: int = 30,
    source: str = "web",
    notes: str = "",
    weekly_availability: Optional[Any] = None,
    blocked_dates: Optional[Any] = None,
    working_hours: Optional[Any] = None,
    business_name: Optional[str] = None,
):
    try:
        if not calendar_id or not sheet_id:
            return False

        booking_dt = parse_datetime(date, time, timezone)

        duration_minutes = duration_minutes or 30

        if not check_availability(
            date,
            time,
            calendar_id,
            timezone,
            duration_minutes=duration_minutes,
            weekly_availability=weekly_availability,
            blocked_dates=blocked_dates,
            working_hours=working_hours,
        ):
            return False

        start_time = booking_dt
        end_time = start_time + timedelta(minutes=duration_minutes)

        event = {
            'summary': f'Appointment with {name}',
            'description': f'Phone: {phone}',
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': timezone,
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': timezone,
            },
        }

        service.events().insert(
            calendarId=calendar_id,
            body=event
        ).execute()

        booking_id = generate_human_booking_id(business_name)
        save_to_sheet(
            booking_id=booking_id,
            name=name,
            phone=phone,
            date=start_time.strftime("%Y-%m-%d"),
            time=start_time.strftime("%H:%M"),
            sheet_id=sheet_id,
            status="confirmed",
            source=source,
            notes=notes or "",
        )

        return True

    except Exception as e:
        print("❌ Create Event Error:", repr(e))
        return False