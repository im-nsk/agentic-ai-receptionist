import json
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from google.oauth2 import service_account
from googleapiclient.discovery import build
from dateutil import parser

from backend.services.sheets_service import save_to_sheet

# ---------------- GOOGLE CREDENTIALS ---------------- #
SCOPES = ['https://www.googleapis.com/auth/calendar']

credentials_info = json.loads(os.getenv("GOOGLE_CREDENTIALS_JSON"))

credentials = service_account.Credentials.from_service_account_info(
    credentials_info,
    scopes=SCOPES
)

service = build('calendar', 'v3', credentials=credentials)


# ---------------- PARSER ---------------- #

def parse_datetime(date, time, timezone):
    try:
        # Parse natural language
        dt = parser.parse(f"{date} {time}", fuzzy=True)

        # Attach timezone (VERY IMPORTANT)
        tz = ZoneInfo(timezone)
        dt = dt.replace(tzinfo=tz)

        return dt

    except Exception:
        raise ValueError(f"Invalid date/time input: {date} {time}")


# ---------------- VALIDATIONS ---------------- #

def is_valid_slot(dt):
    return dt.minute in [0, 30]


def is_within_working_hours(dt):
    return 9 <= dt.hour < 18


# ---------------- CHECK AVAILABILITY ---------------- #

def check_availability(date, time, calendar_id, timezone):

    booking_dt = parse_datetime(date, time, timezone)

    # Convert to UTC for Google Calendar
    start_time = booking_dt.astimezone(ZoneInfo("UTC"))
    end_time = start_time + timedelta(minutes=30)

    # ❌ Past time
    if start_time <= datetime.now(ZoneInfo("UTC")):
        return False

    # ❌ Invalid slot
    if not is_valid_slot(booking_dt):
        return False

    # ❌ Outside working hours
    if not is_within_working_hours(booking_dt):
        return False

    events = service.events().list(
        calendarId=calendar_id,
        timeMin=start_time.isoformat(),
        timeMax=end_time.isoformat()
    ).execute()

    return len(events.get('items', [])) == 0


# ---------------- CREATE EVENT ---------------- #

def create_event(name, phone, date, time, calendar_id, sheet_id, timezone):
    try:
        booking_dt = parse_datetime(date, time, timezone)

        if not check_availability(date, time, calendar_id, timezone):
            return False

        start_time_local = booking_dt
        end_time_local = start_time_local + timedelta(minutes=30)

        event = {
            'summary': f'Appointment with {name}',
            'description': f'Phone: {phone}',
            'start': {
                'dateTime': start_time_local.isoformat(),
                'timeZone': timezone,
            },
            'end': {
                'dateTime': end_time_local.isoformat(),
                'timeZone': timezone,
            },
        }

        service.events().insert(
            calendarId=calendar_id,
            body=event
        ).execute()

        # Save to sheet (local readable time)
        save_to_sheet(
            name,
            phone,
            start_time_local.strftime("%Y-%m-%d"),
            start_time_local.strftime("%H:%M"),
            sheet_id=sheet_id
        )

        return True

    except Exception as e:
        print("❌ Create Event Error:", repr(e))
        return False