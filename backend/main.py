"""
FastAPI app — auth (OTP), client setup, booking (web + VAPI).
"""

from __future__ import annotations

import json
import secrets
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.db.database import Base, SessionLocal, engine
from backend.db.migrate import migrate_schema
from backend.models.booking import BookingRequest
from backend.models.client import Client
from backend.models.email_otp import EmailOTP
from backend.services.auth_service import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)
from backend.services.calendar_service import check_availability, create_event
from backend.services.sms_service import send_sms

# ---------------- INIT ---------------- #
app = FastAPI()

Base.metadata.create_all(bind=engine)
migrate_schema(engine)

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


def get_current_client_id(authorization: str = Header(None)):
    if not authorization or " " not in authorization:
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        token = authorization.split(" ")[1]
        payload = decode_token(token)
        return payload["client_id"]
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


def _client_slot_minutes(client: Client) -> int:
    v = client.slot_duration or 30
    return int(v) if v > 0 else 30


def _digits_phone(p: Optional[str]) -> str:
    if not p:
        return ""
    return "".join(ch for ch in p if ch.isdigit())


def _phones_match(stored: Optional[str], incoming: str) -> bool:
    a = _digits_phone(stored)
    b = _digits_phone(incoming)
    if len(b) < 10:
        return False
    if not a:
        return False
    if a == b:
        return True
    return a[-10:] == b[-10:]


def _client_by_business_phone(db: Session, phone_number: str) -> Optional[Client]:
    pn = phone_number.strip()
    if not pn:
        return None
    for row in db.query(Client).limit(5000):  # simple MVP routing
        if row.phone_number and _phones_match(row.phone_number, pn):
            return row
    return None


def _generate_otp_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


# ---------------- REQUEST MODELS ---------------- #
class SignupRequest(BaseModel):
    name: str
    email: str
    password: str


class VerifyOTPRequest(BaseModel):
    email: str
    code: str = Field(..., min_length=6, max_length=6)


class LoginRequest(BaseModel):
    email: str
    password: str


class SetupRequest(BaseModel):
    calendar_id: str
    sheet_id: str
    timezone: Optional[str] = None
    phone_number: Optional[str] = None
    business_name: Optional[str] = None
    working_hours: Optional[str] = None
    slot_duration: Optional[int] = Field(default=None, ge=15, le=480)
    services: Optional[List[str]] = None
    free_text: Optional[str] = None


class VapiCheckRequest(BaseModel):
    phone_number: str = Field(..., description="Business line / client booking number")
    date: str
    time: str


class VapiBookRequest(BaseModel):
    phone_number: str = Field(..., description="Business line / client booking number")
    name: str = Field(..., min_length=2)
    phone: str
    date: str
    time: str


# ---------------- HEALTH ---------------- #
@app.get("/")
def home():
    return {"message": "AI Receptionist Backend Running"}


# ---------------- SIGNUP (+ OTP draft) ---------------- #
@app.post("/signup")
def signup(data: SignupRequest, db: Session = Depends(get_db)):
    existing = db.query(Client).filter(Client.email == data.email.strip().lower()).first()

    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")

    email = data.email.strip().lower()

    try:
        client = Client(
            name=data.name.strip(),
            email=email,
            password=hash_password(data.password),
            email_verified=False,
        )
        db.add(client)
        db.flush()

        code = _generate_otp_code()
        expires_at = datetime.utcnow() + timedelta(minutes=15)
        db.query(EmailOTP).filter(EmailOTP.email == email).delete()
        db.add(EmailOTP(email=email, code=code, expires_at=expires_at))
        db.commit()

        print(f"[MVP EMAIL] OTP for {email}: {code} (expires ~15m from signup, UTC naive)")

        return {"status": "pending_verification", "email": email}

    except Exception as e:
        db.rollback()
        print("SIGNUP ERROR:", repr(e))
        raise HTTPException(status_code=500, detail="Signup failed")


# ---------------- VERIFY OTP ---------------- #
@app.post("/verify-otp")
def verify_otp(payload: VerifyOTPRequest, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()

    row = db.query(EmailOTP).filter(EmailOTP.email == email).first()
    if not row:
        raise HTTPException(status_code=400, detail="Invalid or expired code")

    if row.expires_at < datetime.utcnow():
        db.delete(row)
        db.commit()
        raise HTTPException(status_code=400, detail="OTP expired")

    if row.code.strip() != payload.code.strip():
        raise HTTPException(status_code=400, detail="Invalid code")

    client = db.query(Client).filter(Client.email == email).first()
    if not client:
        db.delete(row)
        db.commit()
        raise HTTPException(status_code=404, detail="User not found")

    client.email_verified = True
    db.delete(row)
    db.commit()

    token = create_access_token({"client_id": client.id})

    return {"access_token": token}


# ---------------- LOGIN ---------------- #
@app.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    client = db.query(Client).filter(Client.email == data.email.strip().lower()).first()

    if not client or not verify_password(data.password, client.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not bool(client.email_verified):
        raise HTTPException(status_code=403, detail="Verify your email with the OTP we sent.")

    token = create_access_token({"client_id": client.id})
    return {"access_token": token}


# ---------------- CLIENT ---------------- #
def _services_list(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    try:
        v = json.loads(raw)
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()]
    except (json.JSONDecodeError, TypeError):
        pass
    return []


@app.get("/client")
def get_client_data(
    client_id: str = Depends(get_current_client_id),
    db: Session = Depends(get_db),
):
    client = db.query(Client).filter(Client.id == client_id).first()

    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    setup_ready = bool(client.calendar_id and client.sheet_id)
    svc = _services_list(client.services_json)

    return {
        "name": client.name,
        "minutes_used": client.minutes_used,
        "plan_limit": client.plan_limit,
        "calendar_id": client.calendar_id or "",
        "sheet_id": client.sheet_id or "",
        "timezone": client.timezone or "America/New_York",
        "phone_number": client.phone_number or "",
        "setup_complete": setup_ready,
        "business_name": client.business_name or "",
        "working_hours": client.working_hours or "",
        "slot_duration": client.slot_duration or 30,
        "services": svc,
        "free_text": client.free_text or "",
    }


# ---------------- SETUP (UPSERT SAME ROW) ---------------- #
@app.post("/setup")
def setup(
    data: SetupRequest,
    client_id: str = Depends(get_current_client_id),
    db: Session = Depends(get_db),
):
    client = db.query(Client).filter(Client.id == client_id).first()

    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    client.calendar_id = data.calendar_id.strip()
    client.sheet_id = data.sheet_id.strip()

    if data.timezone is not None:
        client.timezone = data.timezone.strip() or client.timezone
    if data.phone_number is not None:
        client.phone_number = data.phone_number.strip() or None
    if data.business_name is not None:
        client.business_name = data.business_name.strip() or None
    if data.working_hours is not None:
        client.working_hours = data.working_hours.strip() or None
    if data.slot_duration is not None:
        client.slot_duration = data.slot_duration
    if data.services is not None:
        client.services_json = json.dumps([s.strip() for s in data.services if s.strip()]) if data.services else None
    if data.free_text is not None:
        client.free_text = data.free_text.strip() or None

    db.commit()
    db.refresh(client)

    return {"status": "saved"}


# ---------------- AVAILABILITY / BOOK SHARED ---------------- #
def _run_availability(client: Client, date: str, time: str) -> dict:
    if not client.calendar_id:
        return {"available": False, "message": "Client setup incomplete"}
    duration = _client_slot_minutes(client)
    ok = check_availability(
        date,
        time,
        calendar_id=client.calendar_id,
        timezone=client.timezone or "America/New_York",
        duration_minutes=duration,
    )
    return {"available": ok, "message": "Available" if ok else "Slot not available"}


def _run_book_background(client: Client, name: str, phone: str, date: str, time: str, background_tasks: BackgroundTasks) -> dict:
    if not client.calendar_id or not client.sheet_id:
        raise HTTPException(status_code=400, detail="Client setup incomplete")

    duration = _client_slot_minutes(client)
    ok = create_event(
        name,
        phone,
        date,
        time,
        calendar_id=client.calendar_id,
        sheet_id=client.sheet_id,
        timezone=client.timezone or "America/New_York",
        duration_minutes=duration,
    )

    if not ok:
        return {"status": "failed", "message": "Could not create booking"}

    background_tasks.add_task(
        send_sms,
        phone,
        f"Hi {name}, your appointment is confirmed on {date} at {time}",
    )

    return {"status": "confirmed", "message": "Booking confirmed"}


@app.post("/check-availability")
def availability(
    req: BookingRequest,
    client_id: str = Depends(get_current_client_id),
    db: Session = Depends(get_db),
):
    try:
        client = db.query(Client).filter(Client.id == client_id).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        return _run_availability(client, req.date, req.time)
    except HTTPException:
        raise
    except Exception as e:
        print("Availability Error:", repr(e))
        raise HTTPException(status_code=500, detail="Availability failed")


@app.post("/book-appointment")
def book_web(
    req: BookingRequest,
    background_tasks: BackgroundTasks,
    client_id: str = Depends(get_current_client_id),
    db: Session = Depends(get_db),
):
    try:
        client = db.query(Client).filter(Client.id == client_id).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        result = _run_book_background(client, req.name, req.phone, req.date, req.time, background_tasks)
        return result

    except HTTPException:
        raise
    except Exception as e:
        print("Booking Error:", repr(e))
        raise HTTPException(status_code=500, detail="Booking failed")


# ---------------- VAPI (phone → client) ---------------- #
@app.post("/vapi/check-availability")
def vapi_check(payload: VapiCheckRequest, db: Session = Depends(get_db)):
    client = _client_by_business_phone(db, payload.phone_number)
    if not client:
        raise HTTPException(status_code=404, detail="Unknown business phone")
    return _run_availability(client, payload.date, payload.time)


@app.post("/vapi/book")
def vapi_book(payload: VapiBookRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    client = _client_by_business_phone(db, payload.phone_number)
    if not client:
        raise HTTPException(status_code=404, detail="Unknown business phone")
    try:
        return _run_book_background(
            client,
            payload.name,
            payload.phone,
            payload.date,
            payload.time,
            background_tasks,
        )
    except HTTPException:
        raise
    except Exception as e:
        print("VAPI Booking Error:", repr(e))
        raise HTTPException(status_code=500, detail="Booking failed")
