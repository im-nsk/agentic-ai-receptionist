from fastapi import FastAPI, HTTPException, BackgroundTasks
from models.booking import BookingRequest
from services.calendar_service import check_availability, create_event, parse_datetime
from services.client_services import get_client
from services.sms_service import send_sms
from db.init_db import init_db

init_db()

app = FastAPI()


@app.get("/")
def home():
    return {"message": "AI Receptionist Backend Running"}


@app.post("/check-availability")
def availability(req: BookingRequest):
    try:
        client = get_client(req.client_id)

        if not client:
            return {"available": False, "message": "Invalid client"}

        booking_dt = parse_datetime(req.date, req.time)

        is_available = check_availability(
            booking_dt,
            calendar_id=client.calendar_id
        )

        return {
            "available": is_available,
            "message": "Available" if is_available else "Slot not available"
        }

    except Exception as e:
        print("❌ Availability Error:", repr(e))
        raise HTTPException(status_code=500, detail="Availability check failed")


@app.post("/book-appointment")
def book(req: BookingRequest, background_tasks: BackgroundTasks):
    try:
        print("📥 Booking Request:", req)

        client = get_client(req.client_id)

        if not client:
            return {"status": "failed", "message": "Invalid client"}

        success = create_event(
            req.name,
            req.phone,
            req.date,
            req.time,
            calendar_id=client.calendar_id,
            sheet_id=client.sheet_id
        )

        if not success:
            return {
                "status": "failed",
                "message": "Slot unavailable or invalid"
            }

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