import json
import os
from datetime import datetime, timedelta

from google.oauth2 import service_account
from googleapiclient.discovery import build
from dateutil import parser

from services.sheets_service import save_to_sheet

# ---------------- CONFIG ---------------- #
SCOPES = ['https://www.googleapis.com/auth/calendar']
calendar_id = 'nishantnayan2002@gmail.com'  # later make dynamic

# ---------------- GOOGLE CREDENTIALS ---------------- #
credentials_info = json.loads(os.getenv("GOOGLE_CREDENTIALS_JSON"))

credentials = service_account.Credentials.from_service_account_info(
    credentials_info,
    scopes=SCOPES
)

service = build('calendar', 'v3', credentials=credentials)


# ---------------- PARSER (CORE LOGIC) ---------------- #

def parse_datetime(date, time):
    """
    Handles ANY natural language input
    Examples:
    - "April 25", "11:00"
    - "tomorrow", "9am"
    - "next Monday", "3 PM"
    """
    try:
        dt = parser.parse(f"{date} {time}", fuzzy=True)

        # Force timezone consistency (important for Google Calendar)
        return dt

    except Exception:
        raise ValueError(f"Invalid date/time input: {date} {time}")


# ---------------- VALIDATIONS ---------------- #

def is_future_datetime(date, time):
    booking_dt = parse_datetime(date, time)
    return booking_dt > datetime.now()


def is_valid_slot(dt):
    """
    Only allow 30-min slots
    """
    return dt.minute in [0, 30]


def is_within_working_hours(dt):
    """
    Example: 9 AM – 6 PM
    """
    return 9 <= dt.hour < 18


# ---------------- CHECK AVAILABILITY ---------------- #

def check_availability(date, time):

    booking_dt = parse_datetime(date, time)

    # ❌ Past time
    if booking_dt <= datetime.now():
        return False

    # ❌ Invalid slot (like 10:17)
    if not is_valid_slot(booking_dt):
        return False

    # ❌ Outside working hours
    if not is_within_working_hours(booking_dt):
        return False

    start_time = booking_dt
    end_time = start_time + timedelta(minutes=30)

    events = service.events().list(
        calendarId=calendar_id,
        timeMin=start_time.isoformat() + 'Z',
        timeMax=end_time.isoformat() + 'Z'
    ).execute()

    return len(events.get('items', [])) == 0


# ---------------- CREATE EVENT ---------------- #

def create_event(name, phone, date, time):

    booking_dt = parse_datetime(date, time)

    if not check_availability(date, time):
        return False

    start_time = booking_dt
    end_time = start_time + timedelta(minutes=30)

    event = {
        'summary': f'Appointment with {name}',
        'description': f'Phone: {phone}',
        'start': {
            'dateTime': start_time.isoformat(),
            'timeZone': 'Asia/Kolkata',
        },
        'end': {
            'dateTime': end_time.isoformat(),
            'timeZone': 'Asia/Kolkata',
        },
    }

    service.events().insert(
        calendarId=calendar_id,
        body=event
    ).execute()

    # ✅ Save to Google Sheet
    save_to_sheet(name, phone, start_time.strftime("%Y-%m-%d"), start_time.strftime("%H:%M"))

    return True