# from twilio.rest import Client
# import os

# account_sid = os.getenv("TWILIO_SID")
# auth_token = os.getenv("TWILIO_AUTH_TOKEN")
# twilio_number = os.getenv("TWILIO_PHONE")

# client = Client(account_sid, auth_token)


# def send_sms(phone, message):
#     client.messages.create(
#         body=message,
#         from_=twilio_number,
#         to=phone
#     )


from twilio.rest import Client
import os
from dotenv import load_dotenv

load_dotenv()

client = Client(
    os.getenv("TWILIO_SID"),
    os.getenv("TWILIO_AUTH_TOKEN")
)

def send_sms(phone, message):
    print("🚀 SMS FUNCTION CALLED")
    
    client.messages.create(
        body=message,
        from_=os.getenv("TWILIO_PHONE"),
        to=phone
    )
    
# def send_sms(phone, message):
#     client.messages.create(
#         body=message,
#         from_=os.getenv("TWILIO_PHONE"),
#         to=phone
#     )