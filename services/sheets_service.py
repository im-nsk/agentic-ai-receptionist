import gspread
import os
import json
from google.oauth2 import service_account
from datetime import datetime

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]


def get_sheet():
    try:
        credentials_info = json.loads(os.getenv("GOOGLE_CREDENTIALS_JSON"))

        credentials = service_account.Credentials.from_service_account_info(
            credentials_info,
            scopes=SCOPES
        )

        client = gspread.authorize(credentials)

        sheet = client.open_by_key("1YHojucUGtfjuGWNTd7_fjDRZfnfbaaOBT9vUyo3XLI8").sheet1

        return sheet

    except Exception as e:
        print("❌ INIT SHEET ERROR:", repr(e))
        raise e


def save_to_sheet(name, phone, date, time, status="Booked"):
    try:
        sheet = get_sheet()

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