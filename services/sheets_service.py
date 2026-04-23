import gspread
import os
import json
from google.oauth2.service_account import Credentials
from datetime import datetime

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# ✅ SAFE ENV LOADING
env_data = os.getenv("GOOGLE_CREDENTIALS_JSON")

if not env_data:
    raise Exception("❌ GOOGLE_CREDENTIALS_JSON is missing in environment variables")

try:
    credentials_info = json.loads(env_data)
except Exception as e:
    raise Exception(f"❌ Invalid JSON in GOOGLE_CREDENTIALS_JSON: {str(e)}")

# ✅ CREATE CREDENTIALS
credentials = Credentials.from_service_account_info(
    credentials_info,
    scopes=SCOPES
)

client = gspread.authorize(credentials)

# ✅ OPEN SHEET
sheet = client.open("Clinic_Appointments").sheet1


def save_to_sheet(name, phone, date, time, status="Booked"):
    sheet.append_row([
        name,
        phone,
        date,
        time,
        status,
        str(datetime.now())
    ])