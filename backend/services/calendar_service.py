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
    candidate_slot_times_for_date,
    effective_weekly_availability,
    is_date_blocked,
    is_slot_on_duration_grid,
    minutes_window_for_date,
    normalize_blocked_dates,
    weekday_key_from_date_iso,
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
    mins = booking_dt.hour * 60 + booking_dt.minute
    if not is_slot_on_duration_grid(mins, open_m, duration_minutes):
        return False
    if not is_within_booking_window(booking_dt, open_m, close_m):
        return False
    return True


def _log_availability_check(
    *,
    date: str,
    time: str,
    timezone: str,
    duration_minutes: int,
    weekly_availability: Optional[Any],
    blocked_dates: Optional[Any],
    working_hours: Optional[Any],
    tenant_ok: bool,
    calendar_ok: Optional[bool],
    final_ok: bool,
    busy_count: Optional[int] = None,
    calendar_error: Optional[str] = None,
) -> None:
    date_str = str(date).strip()
    candidates = candidate_slot_times_for_date(
        weekly_availability,
        working_hours,
        blocked_dates,
        date_str,
        duration_minutes,
    )
    weekly_eff = effective_weekly_availability(weekly_availability, working_hours)
    try:
        day_key = weekday_key_from_date_iso(date_str)
    except Exception:
        day_key = "?"
    print(
        "AVAILABILITY check:",
        f"date={date_str!r}",
        f"time={time!r}",
        f"timezone={timezone!r}",
        f"duration_min={duration_minutes}",
        f"weekday={day_key!r}",
        f"weekly_day={weekly_eff.get(day_key) if day_key else None!r}",
        f"blocked_dates={normalize_blocked_dates(blocked_dates)!r}",
        f"candidate_slots({len(candidates)})={candidates!r}",
        f"tenant_rules_ok={tenant_ok}",
        f"calendar_ok={calendar_ok}",
        f"calendar_busy={busy_count}",
        f"calendar_error={calendar_error!r}" if calendar_error else "calendar_error=None",
        f"final_available={final_ok}",
    )


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
        _log_availability_check(
            date=str(date),
            time=str(time),
            timezone=str(timezone),
            duration_minutes=duration_minutes or 30,
            weekly_availability=weekly_availability,
            blocked_dates=blocked_dates,
            working_hours=working_hours,
            tenant_ok=False,
            calendar_ok=None,
            final_ok=False,
            calendar_error="invalid_date_or_time",
        )
        return False

    duration_minutes = duration_minutes or 30
    date_str = str(date).strip()

    start_time = booking_dt.astimezone(ZoneInfo("UTC"))
    end_time = start_time + timedelta(minutes=duration_minutes)

    # Past
    if start_time <= datetime.now(ZoneInfo("UTC")):
        _log_availability_check(
            date=date_str,
            time=str(time),
            timezone=str(timezone),
            duration_minutes=duration_minutes,
            weekly_availability=weekly_availability,
            blocked_dates=blocked_dates,
            working_hours=working_hours,
            tenant_ok=False,
            calendar_ok=None,
            final_ok=False,
            calendar_error="slot_in_past",
        )
        return False

    tenant_ok = _tenant_rules_ok(
        booking_dt,
        date_str,
        duration_minutes,
        weekly_availability,
        blocked_dates,
        working_hours,
    )
    if not tenant_ok:
        _log_availability_check(
            date=date_str,
            time=str(time),
            timezone=str(timezone),
            duration_minutes=duration_minutes,
            weekly_availability=weekly_availability,
            blocked_dates=blocked_dates,
            working_hours=working_hours,
            tenant_ok=False,
            calendar_ok=None,
            final_ok=False,
        )
        return False

    if not calendar_id:
        _log_availability_check(
            date=date_str,
            time=str(time),
            timezone=str(timezone),
            duration_minutes=duration_minutes,
            weekly_availability=weekly_availability,
            blocked_dates=blocked_dates,
            working_hours=working_hours,
            tenant_ok=True,
            calendar_ok=None,
            final_ok=True,
            calendar_error="no_calendar_id_schedule_only",
        )
        return True

    calendar_ok: Optional[bool] = None
    busy_count: Optional[int] = None
    calendar_error: Optional[str] = None
    try:
        events = service.events().list(
            calendarId=calendar_id,
            timeMin=start_time.isoformat(),
            timeMax=end_time.isoformat(),
            singleEvents=True,
        ).execute()
        busy_count = len(events.get("items", []))
        calendar_ok = busy_count == 0
    except HttpError as e:
        calendar_error = google_http_error_message(e)
        print(
            "AVAILABILITY calendar HttpError:",
            f"status={google_http_status(e)}",
            f"calendar_id={calendar_id!r}",
            f"api_message={calendar_error!r}",
        )
        calendar_ok = True
    except Exception as e:
        calendar_error = repr(e)
        print("AVAILABILITY calendar unexpected:", calendar_error, f"calendar_id={calendar_id!r}")
        calendar_ok = True

    final_ok = bool(tenant_ok and calendar_ok)
    _log_availability_check(
        date=date_str,
        time=str(time),
        timezone=str(timezone),
        duration_minutes=duration_minutes,
        weekly_availability=weekly_availability,
        blocked_dates=blocked_dates,
        working_hours=working_hours,
        tenant_ok=tenant_ok,
        calendar_ok=calendar_ok,
        final_ok=final_ok,
        busy_count=busy_count,
        calendar_error=calendar_error,
    )
    return final_ok


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