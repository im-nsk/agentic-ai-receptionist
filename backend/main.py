"""
main.py — Production-ready FastAPI backend
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from backend.db.database import SessionLocal
from backend.db.init_db import init_db
from backend.models.booking import BookingRequest
from backend.models.client import Client
from backend.services.calendar_service import check_availability, create_event, parse_datetime
from backend.services.sms_service import send_sms
from backend.services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    decode_token
)


# ---------------- INIT ---------------- #
init_db()
app = FastAPI()


# ---------------- CORS ---------------- #
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------- DB ---------------- #
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------- AUTH ---------------- #
def get_current_client_id(authorization: str = Header()):
    try:
        if not authorization or " " not in authorization:
            raise Exception()

        token = authorization.split(" ")[1]
        payload = decode_token(token)
        return payload["client_id"]

    except:
        raise HTTPException(status_code=401, detail="Invalid token")


# ---------------- HEALTH ---------------- #
@app.get("/")
def home():
    return {"message": "AI Receptionist Backend Running"}


# ---------------- SIGNUP ---------------- #
@app.post("/signup")
def signup(data: dict, db: Session = Depends(get_db)):

    existing = db.query(Client).filter(Client.email == data["email"]).first()

    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")

    client = Client(
        name=data["name"],
        email=data["email"],
        password=hash_password(data["password"])
    )

    db.add(client)
    db.commit()

    return {"status": "created"}


# ---------------- LOGIN ---------------- #
@app.post("/login")
def login(data: dict, db: Session = Depends(get_db)):

    client = db.query(Client).filter(Client.email == data["email"]).first()

    if not client or not verify_password(data["password"], client.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"client_id": client.id})

    return {"access_token": token}


# ---------------- CLIENT ---------------- #
@app.get("/client")
def get_client_data(
    client_id: str = Depends(get_current_client_id),
    db: Session = Depends(get_db)
):
    client = db.query(Client).filter(Client.id == client_id).first()

    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    return {
        "name": client.name,
        "minutes_used": client.minutes_used,
        "plan_limit": client.plan_limit,
    }


# ---------------- SETUP ---------------- #
@app.post("/setup")
def setup(
    data: dict,
    client_id: str = Depends(get_current_client_id),
    db: Session = Depends(get_db)
):
    client = db.query(Client).filter(Client.id == client_id).first()

    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    client.calendar_id = data.get("calendar_id")
    client.sheet_id = data.get("sheet_id")

    db.commit()

    return {"status": "saved"}


# ---------------- CHECK AVAILABILITY ---------------- #
@app.post("/check-availability")
def availability(
    req: BookingRequest,
    client_id: str = Depends(get_current_client_id),
    db: Session = Depends(get_db)
):
    try:
        client = db.query(Client).filter(Client.id == client_id).first()

        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        booking_dt = parse_datetime(req.date, req.time, client.timezone)

        is_available = check_availability(
            req.date,
            req.time,
            calendar_id=client.calendar_id,
            timezone=client.timezone
        )

        return {
            "available": is_available,
            "message": "Available" if is_available else "Slot not available"
        }

    except Exception as e:
        print("❌ Availability Error:", repr(e))
        raise HTTPException(status_code=500, detail="Availability failed")

# ---------------- BOOK ---------------- #
@app.post("/book-appointment")
def book(
    req: BookingRequest,
    background_tasks: BackgroundTasks,
    client_id: str = Depends(get_current_client_id),
    db: Session = Depends(get_db)
):
    try:
        client = db.query(Client).filter(Client.id == client_id).first()

        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        if not client.calendar_id or not client.sheet_id:
            raise HTTPException(
                status_code=400,
                detail="Client setup incomplete"
            )

        success = create_event(
            req.name,
            req.phone,
            req.date,
            req.time,
            calendar_id=client.calendar_id,
            sheet_id=client.sheet_id,
            timezone=client.timezone
        )

        if not success:
            return {"status": "failed"}

        background_tasks.add_task(
            send_sms,
            req.phone,
            f"Hi {req.name}, your appointment is confirmed on {req.date} at {req.time}"
        )

        return {"status": "confirmed"}

    except Exception as e:
        print("❌ Booking Error:", repr(e))
        raise HTTPException(status_code=500, detail="Booking failed")