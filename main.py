from fastapi import FastAPI, HTTPException, BackgroundTasks
from models.booking import BookingRequest
from services.calendar_service import check_availability, create_event
from services.sms_service import send_sms

app = FastAPI()


# -------- HEALTH CHECK --------
@app.get("/")
def home():
    return {"message": "AI Receptionist Backend Running"}


# -------- CHECK AVAILABILITY --------
@app.post("/check-availability")
def availability(req: BookingRequest):
    try:
        print("🔍 Availability check:", req)

        is_available = check_availability(req.date, req.time)

        return {
            "available": is_available,
            "message": "Available" if is_available else "Slot not available"
        }

    except Exception as e:
        print("❌ Availability Error:", repr(e))
        raise HTTPException(status_code=500, detail="Availability check failed")


# -------- BOOK APPOINTMENT --------
@app.post("/book-appointment")
def book(req: BookingRequest, background_tasks: BackgroundTasks):
    try:
        print("📥 Booking Request:", req)

        # ✅ Single source of truth
        success = create_event(req.name, req.phone, req.date, req.time)

        if not success:
            return {
                "status": "failed",
                "message": "Slot unavailable or invalid"
            }

        # ✅ Background SMS
        background_tasks.add_task(
            send_sms,
            req.phone,
            f"Hi {req.name}, your appointment is confirmed on {req.date} at {req.time}"
        )

        return {
            "status": "confirmed",
            "message": "Appointment booked successfully"
        }

    except Exception as e:
        print("❌ Booking Error:", repr(e))
        raise HTTPException(status_code=500, detail="Booking failed")