import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# Initialize once (global)
creds = Credentials.from_service_account_file(
    "credentials.json",
    scopes=SCOPES
)

client = gspread.authorize(creds)

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