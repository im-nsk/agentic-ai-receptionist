"""
FastAPI app — auth (OTP), client setup, booking (web + VAPI).
"""

from __future__ import annotations

import json
import os
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

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
from backend.services.booking_service import book_appointment_logic, check_availability_logic

# ---------------- INIT ---------------- #
app = FastAPI()

VAPI_API_KEY = os.getenv("VAPI_API_KEY", "my-secret-123")

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


def verify_vapi(x_api_key: Optional[str] = Header(None, alias="x-api-key")):
    """VAPI webhook auth — shared secret header."""
    if not x_api_key or x_api_key != VAPI_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")


def _client_slot_minutes(client: Client) -> int:
    v = client.slot_duration or 30
    return int(v) if v > 0 else 30


def get_client_by_phone(db: Session, to_number: Optional[str]):
    """Multi-tenant lookup: inbound AI / Twilio / VAPI `to_number` must match stored `phone_number`."""
    if not to_number or not str(to_number).strip():
        return None
    return db.query(Client).filter(Client.phone_number == str(to_number).strip()).first()


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
    client_phone: Optional[str] = None
    business_name: Optional[str] = None
    working_hours: Optional[str] = None
    slot_duration: Optional[int] = Field(default=None, ge=15, le=480)
    services: Optional[List[str]] = None
    free_text: Optional[str] = None


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
        "client_phone": client.client_phone or "",
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
    if data.client_phone is not None:
        client.client_phone = data.client_phone.strip() or None
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


# ---------------- AVAILABILITY / BOOK (JWT) ---------------- #
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
        return check_availability_logic(
            date=req.date,
            time=req.time,
            calendar_id=client.calendar_id,
            timezone_str=client.timezone or "America/New_York",
            duration_minutes=_client_slot_minutes(client),
        )
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
        return book_appointment_logic(
            client_id=client.id,
            name=req.name,
            phone=req.phone,
            date=req.date,
            time=req.time,
            calendar_id=client.calendar_id,
            sheet_id=client.sheet_id,
            timezone_str=client.timezone or "America/New_York",
            duration_minutes=_client_slot_minutes(client),
            background_tasks=background_tasks,
        )

    except HTTPException:
        raise
    except Exception as e:
        print("Booking Error:", repr(e))
        raise HTTPException(status_code=500, detail="Booking failed")


def _vapi_str(payload: Dict[str, Any], key: str, label: Optional[str] = None) -> str:
    raw = payload.get(key)
    if raw is None or (isinstance(raw, str) and not str(raw).strip()):
        raise HTTPException(status_code=400, detail=f"Missing {(label or key)}")
    return str(raw).strip()


# ---------------- VAPI (x-api-key + to_number) ---------------- #
@app.post("/vapi/check-availability")
def vapi_check(
    payload: Dict[str, Any],
    db: Session = Depends(get_db),
    _auth: None = Depends(verify_vapi),
):
    to_number_raw = payload.get("to_number")
    to_number = str(to_number_raw).strip() if to_number_raw is not None else ""
    client = get_client_by_phone(db, to_number)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    date = _vapi_str(payload, "date")
    time = _vapi_str(payload, "time")

    return check_availability_logic(
        date=date,
        time=time,
        calendar_id=client.calendar_id,
        timezone_str=client.timezone or "America/New_York",
        duration_minutes=_client_slot_minutes(client),
    )


@app.post("/vapi/book")
def vapi_book(
    payload: Dict[str, Any],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _auth: None = Depends(verify_vapi),
):
    try:
        to_number_raw = payload.get("to_number")
        to_number = str(to_number_raw).strip() if to_number_raw is not None else ""
        client = get_client_by_phone(db, to_number)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        name = _vapi_str(payload, "name")
        phone = _vapi_str(payload, "phone")
        date = _vapi_str(payload, "date")
        time = _vapi_str(payload, "time")

        return book_appointment_logic(
            client_id=client.id,
            name=name,
            phone=phone,
            date=date,
            time=time,
            calendar_id=client.calendar_id,
            sheet_id=client.sheet_id,
            timezone_str=client.timezone or "America/New_York",
            duration_minutes=_client_slot_minutes(client),
            background_tasks=background_tasks,
        )

    except HTTPException:
        raise
    except Exception as e:
        print("VAPI Booking Error:", repr(e))
        raise HTTPException(status_code=500, detail="Booking failed")
