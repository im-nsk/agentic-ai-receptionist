import os
import phonenumbers
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

# ---------- INIT (once) ----------
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE = os.getenv("TWILIO_PHONE")

client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)


# ---------- PHONE NORMALIZATION ----------
def normalize_phone(phone, default_region="US"):
    try:
        parsed = phonenumbers.parse(phone, default_region)

        if not phonenumbers.is_valid_number(parsed):
            raise ValueError("Invalid phone number")

        return phonenumbers.format_number(
            parsed,
            phonenumbers.PhoneNumberFormat.E164
        )

    except Exception as e:
        print("❌ Phone Normalization Error:", repr(e))
        return None


# ---------- SMS SENDER ----------
import time

def send_sms(phone, message, retries=2):
    normalized_phone = normalize_phone(phone)

    if not normalized_phone:
        return False

    for attempt in range(retries + 1):
        try:
            response = client.messages.create(
                body=message,
                from_=TWILIO_PHONE,
                to=normalized_phone
            )
            print("✅ SMS SENT:", response.sid)
            return True

        except TwilioRestException as e:
            print(f"❌ Attempt {attempt+1} failed:", e.msg)
            time.sleep(1)

    return False