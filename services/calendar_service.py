# # booked_slots = []

# # def check_availability(date, time):
# #     slot = f"{date} {time}"
# #     return slot not in booked_slots


# # def create_event(name, phone, date, time):
# #     slot = f"{date} {time}"

# #     if slot in booked_slots:
# #         return False

# #     booked_slots.append(slot)

# #     print(f"Booked: {name} at {slot}")

# #     return True


# from google.oauth2 import service_account
# from googleapiclient.discovery import build
# from datetime import datetime, timedelta

# SCOPES = ['https://www.googleapis.com/auth/calendar']
# SERVICE_ACCOUNT_FILE = 'credentials.json'

# calendar_id = 'nishantnayan2002@gmail.com'  # or your calendar email

# credentials = service_account.Credentials.from_service_account_file(
#     SERVICE_ACCOUNT_FILE, scopes=SCOPES
# )

# service = build('calendar', 'v3', credentials=credentials)


# # 🔍 CHECK AVAILABILITY
# def check_availability(date, time):
#     start_time = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
#     end_time = start_time + timedelta(minutes=30)

#     events = service.events().list(
#         calendarId=calendar_id,
#         timeMin=start_time.isoformat() + 'Z',
#         timeMax=end_time.isoformat() + 'Z'
#     ).execute()

#     return len(events.get('items', [])) == 0


# # 📅 CREATE EVENT
# def create_event(name, phone, date, time):
#     start_time = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
#     end_time = start_time + timedelta(minutes=30)

#     event = {
#         'summary': f'Appointment with {name}',
#         'description': f'Phone: {phone}',
#         'start': {
#             'dateTime': start_time.isoformat(),
#             'timeZone': 'Asia/Kolkata',
#         },
#         'end': {
#             'dateTime': end_time.isoformat(),
#             'timeZone': 'Asia/Kolkata',
#         },
#     }

#     service.events().insert(calendarId=calendar_id, body=event).execute()
#     return True

# from datetime import datetime

# def is_future_datetime(date, time):
#     booking_dt = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
#     return booking_dt > datetime.now()

# def is_within_working_hours(time):
#     hour = int(time.split(":")[0])
#     return 9 <= hour < 18  # 9 AM to 6 PM

# def check_availability(date, time):
#     # ❌ Block past bookings
#     if not is_future_datetime(date, time):
#         return False

#     # ❌ Block outside working hours
#     if not is_within_working_hours(time):
#         return False



import json
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta

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

def normalize_date(date_str):
    date_str = date_str.lower().strip()

    if date_str == "today":
        return datetime.now().strftime("%Y-%m-%d")

    elif date_str == "tomorrow":
        return (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    return date_str

# ---------------- VALIDATIONS ---------------- #

def is_future_datetime(date, time):
    date = normalize_date(date)  # 🔥 add this
    booking_dt = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")

    return booking_dt > datetime.now()


# def is_within_working_hours(time):
#     hour = int(time.split(":")[0])
#     return 9 <= hour < 18  # 9 AM to 6 PM


def is_valid_slot(time):
    minutes = int(time.split(":")[1])
    return minutes in [0, 30]  # only 00 or 30


# ---------------- CHECK AVAILABILITY ---------------- #

def check_availability(date, time):

    date = normalize_date(date)

    # ❌ Block past bookings
    if not is_future_datetime(date, time):
        return False

    # ❌ Block outside working hours
    # if not is_within_working_hours(time):
    #     return False

    # ❌ Invalid slot (like 10:17)
    if not is_valid_slot(time):
        return False

    start_time = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
    end_time = start_time + timedelta(minutes=30)

    events = service.events().list(
        calendarId=calendar_id,
        timeMin=start_time.isoformat() + 'Z',
        timeMax=end_time.isoformat() + 'Z'
    ).execute()

    return len(events.get('items', [])) == 0


# ---------------- CREATE EVENT ---------------- #

def create_event(name, phone, date, time):

    date = normalize_date(date)
    
    if not check_availability(date, time):
        return False

    start_time = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
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

    service.events().insert(calendarId=calendar_id, body=event).execute()

    return True