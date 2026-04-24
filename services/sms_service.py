from twilio.rest import Client
import os

client = Client(
    os.getenv("TWILIO_SID"),
    os.getenv("TWILIO_AUTH_TOKEN")
)


def normalize_phone(phone):
    phone = phone.strip()

    # Remove spaces and dashes
    phone = phone.replace(" ", "").replace("-", "")

    # Already international format
    if phone.startswith("+"):
        return phone

    # If 10-digit → assume India (for now)
    if len(phone) == 10:
        return "+91" + phone

    return phone  # fallback


def send_sms(phone, message):
    try:
        print("🚀 SMS FUNCTION CALLED")

        phone = normalize_phone(phone)

        response = client.messages.create(
            body=message,
            from_=os.getenv("TWILIO_PHONE"),
            to=phone
        )

        print("✅ SMS SENT:", response.sid)

    except Exception as e:
        print("❌ SMS ERROR:", repr(e))