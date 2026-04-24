import gspread
import os
import json
from google.oauth2 import service_account
from datetime import datetime

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# 🔥 Initialize ONCE (important)
credentials_info = json.loads(os.getenv("GOOGLE_CREDENTIALS_JSON"))

credentials = service_account.Credentials.from_service_account_info(
    credentials_info,
    scopes=SCOPES
)

client = gspread.authorize(credentials)


def get_sheet(sheet_id):
    try:
        return client.open_by_key(sheet_id).sheet1
    except Exception as e:
        print("❌ INIT SHEET ERROR:", repr(e))
        raise e


def save_to_sheet(name, phone, date, time, sheet_id, status="Booked"):
    try:
        sheet = get_sheet(sheet_id)

        sheet.append_row([
            name,
            phone,
            date,
            time,
            status,
            str(datetime.now())
        ])

        print("✅ Saved to Google Sheet")

    except Exception as e:
        print("❌ Sheet Error:", repr(e))