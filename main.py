from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime
from services.calendar_service import check_availability, create_event
from services.sms_service import send_sms

app = FastAPI()

# -------- REQUEST MODEL --------
class BookingRequest(BaseModel):
    name: str
    phone: str
    date: str   # YYYY-MM-DD
    time: str   # HH:MM

# -------- HEALTH CHECK --------
@app.get("/")
def home():
    return {"message": "AI Receptionist Backend Running"}

# -------- CHECK AVAILABILITY --------
@app.post("/check-availability")
def availability(req: BookingRequest):
    is_available = check_availability(req.date, req.time)

    if is_available:
        return {"available": True}
    else:
        return {"available": False, "message": "Slot not available"}

# -------- BOOK APPOINTMENT --------
# @app.post("/book-appointment")
# def book(req: BookingRequest):
#     success = create_event(req.name, req.phone, req.date, req.time)

#     if success:
#         return {
#             "status": "confirmed",
#             "message": f"Appointment booked for {req.date} at {req.time}"
#         }
#     else:
#         return {"status": "failed"}

@app.post("/book-appointment")
def book(req: BookingRequest):
    success = create_event(req.name, req.phone, req.date, req.time)

    if success:
        # ✅ SEND SMS HERE
        send_sms(
            req.phone,
            f"Hi {req.name}, your appointment is confirmed on {req.date} at {req.time}"
        )

        return {
            "status": "confirmed",
            "message": f"Appointment booked for {req.date} at {req.time}"
        }
    else:
        return {"status": "failed"}