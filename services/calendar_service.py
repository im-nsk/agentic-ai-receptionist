import json
import os
from datetime import datetime, timedelta

from google.oauth2 import service_account
from googleapiclient.discovery import build
from dateutil import parser
import pytz

from services.sheets_service import save_to_sheet

# ---------------- CONFIG ---------------- #
SCOPES = ['https://www.googleapis.com/auth/calendar']

# Default timezone (can be dynamic per client later)
DEFAULT_TIMEZONE = "America/New_York"

# ---------------- GOOGLE CREDENTIALS ---------------- #
credentials_info = json.loads(os.getenv("GOOGLE_CREDENTIALS_JSON"))

credentials = service_account.Credentials.from_service_account_info(
    credentials_info,
    scopes=SCOPES
)

service = build('calendar', 'v3', credentials=credentials)


# ---------------- PARSER (CORE LOGIC) ---------------- #

def parse_datetime(date, time, timezone_str=DEFAULT_TIMEZONE):
    """
    Handles ANY natural language input
    Examples:
    - "April 25", "11:00"
    - "tomorrow", "9am"
    - "next Monday", "3 PM"
    """

    try:
        tz = pytz.timezone(timezone_str)

        dt = parser.parse(f"{date} {time}", fuzzy=True)

        # Make timezone aware
        if dt.tzinfo is None:
            dt = tz.localize(dt)
        else:
            dt = dt.astimezone(tz)

        return dt

    except Exception:
        raise ValueError(f"Invalid date/time input: {date} {time}")


# ---------------- VALIDATIONS ---------------- #

def is_valid_slot(dt):
    return dt.minute in [0, 30]


def is_within_working_hours(dt):
    return 9 <= dt.hour < 18


# ---------------- CHECK AVAILABILITY ---------------- #

def check_availability(booking_dt, calendar_id):

    now = datetime.now(pytz.utc)

    # Convert booking time to UTC for comparison
    booking_dt_utc = booking_dt.astimezone(pytz.utc)

    # ❌ Past time
    if booking_dt_utc <= now:
        return False

    # ❌ Invalid slot
    if not is_valid_slot(booking_dt):
        return False

    # ❌ Outside working hours
    if not is_within_working_hours(booking_dt):
        return False

    start_time = booking_dt_utc
    end_time = start_time + timedelta(minutes=30)

    try:
        events = service.events().list(
            calendarId=calendar_id,
            timeMin=start_time.isoformat(),
            timeMax=end_time.isoformat()
        ).execute()

        return len(events.get('items', [])) == 0

    except Exception as e:
        print("❌ Calendar Availability Error:", repr(e))
        return False


# ---------------- CREATE EVENT ---------------- #

def create_event(name, phone, date, time, calendar_id, sheet_id, timezone=DEFAULT_TIMEZONE):
    try:
        booking_dt = parse_datetime(date, time, timezone)

        if not check_availability(booking_dt, calendar_id):
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

        # ✅ Save to Google Sheet
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