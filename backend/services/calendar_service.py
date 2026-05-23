import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dateutil import parser

from backend.services.google_errors import google_http_error_message, google_http_status
from backend.services.availability_rules import (
    candidate_slot_labels_12h_for_date,
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
SCOPES = ["https://www.googleapis.com/auth/calendar"]

_calendar_api = None


def get_calendar_api():
    """Lazy Calendar API client; None when credentials are missing or invalid."""
    global _calendar_api
    if _calendar_api is not None:
        return _calendar_api
    raw = (os.getenv("GOOGLE_CREDENTIALS_JSON") or "").strip()
    if not raw:
        print("CALENDAR: GOOGLE_CREDENTIALS_JSON is not set")
        return None
    try:
        credentials_info = json.loads(raw)
        credentials = service_account.Credentials.from_service_account_info(
            credentials_info,
            scopes=SCOPES,
        )
        _calendar_api = build("calendar", "v3", credentials=credentials)
        return _calendar_api
    except Exception as e:
        print("CALENDAR: failed to initialize API client:", repr(e))
        return None


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

    cal_api = get_calendar_api()
    if cal_api is None:
        raise CalendarAccessNotGrantedError(
            "Google Calendar credentials are not configured on the server."
        )
    try:
        cal_api.events().list(
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


def canonical_date_str_from_booking_dt(booking_dt: datetime, timezone: str) -> str:
    """YYYY-MM-DD in tenant timezone (for rules that require ISO dates)."""
    tz = ZoneInfo((timezone or "").strip() or "America/New_York")
    local = booking_dt.astimezone(tz) if booking_dt.tzinfo else booking_dt.replace(tzinfo=tz)
    return local.strftime("%Y-%m-%d")


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


def _availability_payload(
    available: bool,
    *,
    availability_check_failed: bool = False,
    message: str = "",
) -> dict:
    return {
        "available": bool(available),
        "availability_check_failed": bool(availability_check_failed),
        "message": message
        or ("Available" if available else "Slot not available"),
    }


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
    calendar_id: Optional[str] = None,
) -> None:
    try:
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
            f"calendar_id={calendar_id!r}",
            f"date={date_str!r}",
            f"time={time!r}",
            f"timezone={timezone!r}",
            f"duration_min={duration_minutes}",
            f"weekday={day_key!r}",
            f"weekly_day={weekly_eff.get(day_key) if day_key in weekly_eff else None!r}",
            f"blocked_dates={normalize_blocked_dates(blocked_dates)!r}",
            f"candidate_slots({len(candidates)})={candidates!r}",
            f"tenant_rules_ok={tenant_ok}",
            f"calendar_ok={calendar_ok}",
            f"calendar_busy={busy_count}",
            f"calendar_error={calendar_error!r}" if calendar_error else "calendar_error=None",
            f"final_available={final_ok}",
        )
    except Exception as e:
        print("AVAILABILITY log error:", repr(e))


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
    date_str = canonical_date_str_from_booking_dt(booking_dt, timezone)
    return _tenant_rules_ok(
        booking_dt,
        date_str,
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
) -> dict:
    cal_id = (calendar_id or "").strip() or None
    duration_minutes = duration_minutes or 30

    try:
        booking_dt = parse_datetime(date, time, timezone)
    except Exception:
        _log_availability_check(
            date=str(date),
            time=str(time),
            timezone=str(timezone),
            duration_minutes=duration_minutes,
            weekly_availability=weekly_availability,
            blocked_dates=blocked_dates,
            working_hours=working_hours,
            tenant_ok=False,
            calendar_ok=None,
            final_ok=False,
            calendar_error="invalid_date_or_time",
            calendar_id=cal_id,
        )
        return _availability_payload(False, message="Invalid date or time.")

    date_str = canonical_date_str_from_booking_dt(booking_dt, timezone)
    start_time = booking_dt.astimezone(ZoneInfo("UTC"))
    end_time = start_time + timedelta(minutes=duration_minutes)

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
            calendar_id=cal_id,
        )
        return _availability_payload(
            False,
            message="That time has already passed for your business timezone.",
        )

    try:
        tenant_ok = _tenant_rules_ok(
            booking_dt,
            date_str,
            duration_minutes,
            weekly_availability,
            blocked_dates,
            working_hours,
        )
    except Exception as e:
        print("AVAILABILITY tenant_rules error:", repr(e), f"date={date_str!r}")
        tenant_ok = False

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
            calendar_id=cal_id,
        )
        return _availability_payload(False)

    if not cal_id:
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
            calendar_id=cal_id,
        )
        return _availability_payload(True)

    calendar_ok: Optional[bool] = None
    busy_count: Optional[int] = None
    calendar_error: Optional[str] = None
    cal_api = get_calendar_api()
    if cal_api is None:
        calendar_error = "google_credentials_not_configured"
        calendar_ok = True
    else:
        try:
            events = cal_api.events().list(
                calendarId=cal_id,
                timeMin=start_time.isoformat(),
                timeMax=end_time.isoformat(),
                singleEvents=True,
            ).execute()
            busy_count = len(events.get("items", []))
            calendar_ok = busy_count == 0
            print(
                "AVAILABILITY calendar list:",
                f"calendar_id={cal_id!r}",
                f"busy_count={busy_count}",
                f"timeMin={start_time.isoformat()!r}",
                f"timeMax={end_time.isoformat()!r}",
            )
        except HttpError as e:
            calendar_error = google_http_error_message(e)
            print(
                "AVAILABILITY calendar HttpError:",
                f"status={google_http_status(e)}",
                f"calendar_id={cal_id!r}",
                f"api_message={calendar_error!r}",
            )
            calendar_ok = True
        except Exception as e:
            calendar_error = repr(e)
            print(
                "AVAILABILITY calendar unexpected:",
                calendar_error,
                f"calendar_id={cal_id!r}",
            )
            calendar_ok = True

    calendar_failed = bool(calendar_error)
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
        calendar_id=cal_id,
    )
    if calendar_failed:
        return _availability_payload(
            tenant_ok,
            availability_check_failed=True,
            message="Calendar check unavailable; using schedule-only availability.",
        )
    return _availability_payload(final_ok)


def _parse_google_event_bounds(ev: dict, fallback_tz: str) -> Optional[tuple[datetime, datetime]]:
    """Return (start_utc, end_utc) for a Google Calendar event item."""
    start_obj = ev.get("start") or {}
    end_obj = ev.get("end") or {}
    start_raw = start_obj.get("dateTime") or start_obj.get("date")
    end_raw = end_obj.get("dateTime") or end_obj.get("date")
    if not start_raw or not end_raw:
        return None
    try:
        start_dt = parser.parse(str(start_raw))
        end_dt = parser.parse(str(end_raw))
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=ZoneInfo(fallback_tz))
        if end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=ZoneInfo(fallback_tz))
        return start_dt.astimezone(ZoneInfo("UTC")), end_dt.astimezone(ZoneInfo("UTC"))
    except Exception:
        return None


def _slot_overlaps_events(
    slot_start_utc: datetime,
    slot_end_utc: datetime,
    events: list,
    fallback_tz: str,
) -> bool:
    for ev in events:
        bounds = _parse_google_event_bounds(ev, fallback_tz)
        if not bounds:
            continue
        ev_start, ev_end = bounds
        if slot_start_utc < ev_end and slot_end_utc > ev_start:
            return True
    return False


def check_day_availability(
    date_str: str,
    calendar_id: Optional[str],
    timezone: str,
    duration_minutes: int = 30,
    weekly_availability: Optional[Any] = None,
    blocked_dates: Optional[Any] = None,
    working_hours: Optional[Any] = None,
) -> dict:
    """One request checks every slot for a day (single Google Calendar list call)."""
    date_str = str(date_str).strip()
    cal_id = (calendar_id or "").strip() or None
    tz = (timezone or "").strip() or "America/New_York"
    duration_minutes = duration_minutes or 30

    labels = candidate_slot_labels_12h_for_date(
        weekly_availability,
        working_hours,
        blocked_dates,
        date_str,
        duration_minutes,
    )
    print(
        "CHECK-DAY-AVAILABILITY:",
        f"calendar_id={cal_id!r}",
        f"date={date_str!r}",
        f"timezone={tz!r}",
        f"duration_min={duration_minutes}",
        f"generated_slots={len(labels)}",
        f"labels={labels!r}",
    )

    slots: Dict[str, bool] = {}
    calendar_error: Optional[str] = None
    events: list = []
    now_utc = datetime.now(ZoneInfo("UTC"))

    win = minutes_window_for_date(weekly_availability, working_hours, date_str)
    day_start_utc = None
    day_end_utc = None
    if win and labels:
        try:
            day_start_utc = parse_datetime(date_str, labels[0], tz).astimezone(ZoneInfo("UTC"))
            last = labels[-1]
            last_dt = parse_datetime(date_str, last, tz).astimezone(ZoneInfo("UTC"))
            day_end_utc = last_dt + timedelta(minutes=duration_minutes)
        except Exception:
            day_start_utc = None
            day_end_utc = None

    if cal_id and day_start_utc and day_end_utc:
        cal_api = get_calendar_api()
        if cal_api is None:
            calendar_error = "google_credentials_not_configured"
        else:
            try:
                result = cal_api.events().list(
                    calendarId=cal_id,
                    timeMin=day_start_utc.isoformat(),
                    timeMax=day_end_utc.isoformat(),
                    singleEvents=True,
                    orderBy="startTime",
                ).execute()
                events = list(result.get("items", []))
                print(
                    "CHECK-DAY-AVAILABILITY calendar:",
                    f"events_fetched={len(events)}",
                    f"timeMin={day_start_utc.isoformat()!r}",
                    f"timeMax={day_end_utc.isoformat()!r}",
                )
            except HttpError as e:
                calendar_error = google_http_error_message(e)
                print(
                    "CHECK-DAY-AVAILABILITY calendar HttpError:",
                    f"status={google_http_status(e)}",
                    f"api_message={calendar_error!r}",
                )
            except Exception as e:
                calendar_error = repr(e)
                print("CHECK-DAY-AVAILABILITY calendar unexpected:", calendar_error)

    for label in labels:
        try:
            booking_dt = parse_datetime(date_str, label, tz)
        except Exception:
            slots[label] = False
            continue

        slot_start = booking_dt.astimezone(ZoneInfo("UTC"))
        slot_end = slot_start + timedelta(minutes=duration_minutes)
        if slot_start <= now_utc:
            slots[label] = False
            continue

        try:
            tenant_ok = _tenant_rules_ok(
                booking_dt,
                date_str,
                duration_minutes,
                weekly_availability,
                blocked_dates,
                working_hours,
            )
        except Exception:
            tenant_ok = False

        if not tenant_ok:
            slots[label] = False
            continue

        if calendar_error or not cal_id:
            slots[label] = True
        else:
            slots[label] = not _slot_overlaps_events(slot_start, slot_end, events, tz)

    available_count = sum(1 for v in slots.values() if v)
    print(
        "CHECK-DAY-AVAILABILITY result:",
        f"available_count={available_count}",
        f"total={len(slots)}",
        f"availability_check_failed={bool(calendar_error)}",
    )

    return {
        "slots": slots,
        "availability_check_failed": bool(calendar_error),
        "message": (
            "Calendar check unavailable; using schedule-only availability."
            if calendar_error
            else "ok"
        ),
        "error": calendar_error,
    }


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
        ).get("available"):
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

        cal_api = get_calendar_api()
        if cal_api is None:
            print("CREATE EVENT: calendar API not configured")
            return False

        cal_api.events().insert(
            calendarId=calendar_id,
            body=event
        ).execute()
        if source == "vapi":
            print(
                "[VOICE CALENDAR CREATED]",
                f"calendar_id={calendar_id!r}",
                f"start={start_time.isoformat()!r}",
            )

        booking_id = generate_human_booking_id(business_name)
        if source == "vapi":
            print("[VOICE SHEET WRITE]", f"sheet_id={sheet_id!r}", f"booking_id={booking_id!r}")
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