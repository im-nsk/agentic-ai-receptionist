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
        dt = parser.parse(f"{date} {time}", fuzzy=True)
        tz = ZoneInfo(timezone)
        return dt.replace(tzinfo=tz)

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

    # ❌ Missing config safety
    if not calendar_id:
        return False

    start_time = booking_dt.astimezone(ZoneInfo("UTC"))
    end_time = start_time + timedelta(minutes=30)

    # ❌ Past
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
        if not calendar_id or not sheet_id:
            return False

        booking_dt = parse_datetime(date, time, timezone)

        if not check_availability(date, time, calendar_id, timezone):
            return False

        start_time = booking_dt
        end_time = start_time + timedelta(minutes=30)

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

        # Save to sheet
        save_to_sheet(
            name,
            phone,
            start_time.strftime("%Y-%m-%d"),
            start_time.strftime("%H:%M"),
            sheet_id=sheet_id
        )

        return True

    except Exception as e:
        print("❌ Create Event Error:", repr(e))
        return False