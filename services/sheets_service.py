import gspread
import os
import json
from google.oauth2.service_account import Credentials
from google.oauth2 import service_account
from datetime import datetime

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

credentials_info = json.loads(os.getenv("GOOGLE_CREDENTIALS_JSON"))

credentials = service_account.Credentials.from_service_account_info(
    credentials_info,
    scopes=SCOPES
)

client = gspread.authorize(credentials)

# Open your sheet
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