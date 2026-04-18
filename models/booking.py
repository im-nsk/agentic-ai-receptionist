from services.sms_service import send_sms

@app.post("/book-appointment")
def book(req: BookingRequest):

    if not check_availability(req.date, req.time):
        return {"status": "failed", "message": "Slot unavailable"}

    create_event(req.name, req.phone, req.date, req.time)

    send_sms(
        req.phone,
        f"Hi {req.name}, your appointment is confirmed on {req.date} at {req.time}"
    )

    return {
        "status": "confirmed",
        "message": "Appointment booked successfully"
    }