"""
FastAPI app — auth (OTP), client setup, booking (web + VAPI).
"""

from __future__ import annotations

import os
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy.orm import Session

from backend.db.database import SessionLocal, engine
from backend.db.migrate import migrate_schema
from backend.models.booking import BookingRequest
from backend.models.client import Client
from backend.services.auth_service import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)
from backend.services.booking_datetime import BookingDatetimeError, assert_booking_start_in_future
from backend.services.booking_service import book_appointment_logic, check_availability_logic
from backend.services.phone_validation import normalize_and_validate_phone
from backend.services.email_service import send_email_otp, send_password_reset_email
from backend.services.sheet_analytics import compute_sheet_analytics, empty_analytics_payload
from backend.services.sheets_service import (
    create_provisioned_booking_sheet,
    delete_booking_data_row,
    ensure_booking_sheet_headers,
    get_data_row_cells,
    list_booking_rows_for_dashboard,
    patch_booking_data_row,
)

# ---------------- INIT ---------------- #
app = FastAPI()

VAPI_API_KEY = os.getenv("VAPI_API_KEY", "my-secret-123")

if os.getenv("APP_ENV", "").lower() in ("production", "prod") and VAPI_API_KEY == "my-secret-123":
    import warnings

    warnings.warn(
        "VAPI_API_KEY is still the development default; set a strong secret in production.",
        stacklevel=1,
    )

migrate_schema(engine)

# ---------------- CORS ---------------- #
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://agentic-ai-receptionist-frontend.onrender.com"],
    # JWT is sent via Authorization header, not cookies — False avoids CORS invalid
    # "*"+"credentials:true" combinations and matches typical browser rules.
    allow_credentials=False,
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


def _parse_client_uuid(client_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(client_id))
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


class EmailOnlyRequest(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def _norm_email(cls, value: str) -> str:
        return value.strip().lower()


class ResetPasswordRequest(BaseModel):
    email: str
    code: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=6)

    @field_validator("email")
    @classmethod
    def _norm_reset_email(cls, value: str) -> str:
        return value.strip().lower()


class SetupPayload(BaseModel):
    client_phone: Optional[str] = None

    calendar_id: str
    sheet_id: Optional[str] = None
    timezone: str

    business_name: str
    working_hours: dict
    slot_duration: int = Field(..., ge=1)
    services: List[Any]
    free_text: Optional[str] = None

    @field_validator("calendar_id", "timezone", "business_name")
    @classmethod
    def _required_non_empty(cls, value: str) -> str:
        v = value.strip()
        if not v:
            raise ValueError("must not be empty")
        return v

    @field_validator("sheet_id")
    @classmethod
    def _sheet_id_optional(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        v = value.strip()
        return v or None

    @field_validator("client_phone")
    @classmethod
    def _client_phone_validate(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        v = value.strip()
        if not v:
            return None
        return normalize_and_validate_phone(v)

    @field_validator("free_text")
    @classmethod
    def _free_text_optional_strip(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        v = value.strip()
        return v or None

    @field_validator("services")
    @classmethod
    def _services_must_be_list(cls, value: List[Any]) -> List[Any]:
        if not isinstance(value, list):
            raise ValueError("services must be a list")
        return value


class BookingPatchRequest(BaseModel):
    date: Optional[str] = None
    time: Optional[str] = None
    status: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    notes: Optional[str] = None

    @model_validator(mode="after")
    def _at_least_one_field(self) -> "BookingPatchRequest":
        data = self.model_dump(exclude_unset=True)
        if not data:
            raise ValueError("At least one field is required")
        return self


# ---------------- HEALTH ---------------- #
@app.get("/")
def home():
    return {"message": "AI Receptionist Backend Running"}


# ---------------- SIGNUP (+ OTP draft) ---------------- #
@app.post("/signup")
def signup(data: SignupRequest, db: Session = Depends(get_db)):
    email = data.email.strip().lower()
    existing = db.query(Client).filter(Client.email == email).first()

    if existing and existing.is_verified:
        raise HTTPException(status_code=400, detail="Email already registered")

    code = _generate_otp_code()
    expires_at = datetime.utcnow() + timedelta(minutes=5)

    try:
        if existing and not existing.is_verified:
            existing.name = data.name.strip()
            existing.password = hash_password(data.password)
            existing.otp_code = code
            existing.otp_expiry = expires_at
            existing.password_reset_otp = None
            existing.password_reset_otp_expiry = None
            db.commit()
            send_email_otp(email, code)
            return {"status": "pending_verification", "email": email}

        client = Client(
            name=data.name.strip(),
            email=email,
            password=hash_password(data.password),
            otp_code=code,
            otp_expiry=expires_at,
            is_verified=False,
        )
        db.add(client)
        db.commit()
        send_email_otp(email, code)
        return {"status": "pending_verification", "email": email}

    except Exception as e:
        db.rollback()
        print("SIGNUP ERROR:", repr(e))
        raise HTTPException(status_code=500, detail="Signup failed")


# ---------------- VERIFY OTP ---------------- #
@app.post("/verify-otp")
def verify_otp(payload: VerifyOTPRequest, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()

    client = db.query(Client).filter(Client.email == email).first()
    if not client:
        raise HTTPException(status_code=404, detail="User not found")

    if not client.otp_expiry or client.otp_expiry < datetime.utcnow():
        raise HTTPException(status_code=400, detail="OTP expired")

    if not client.otp_code or client.otp_code.strip() != payload.code.strip():
        raise HTTPException(status_code=400, detail="Invalid or expired code")

    client.is_verified = True
    client.otp_code = None
    client.otp_expiry = None
    client.password_reset_otp = None
    client.password_reset_otp_expiry = None
    db.commit()

    token = create_access_token({"client_id": str(client.id)})

    return {"access_token": token}


@app.post("/resend-otp")
def resend_otp(data: EmailOnlyRequest, db: Session = Depends(get_db)):
    client = db.query(Client).filter(Client.email == data.email).first()
    if not client:
        raise HTTPException(status_code=404, detail="No pending verification for this email")
    if client.is_verified:
        raise HTTPException(status_code=400, detail="Email is already verified")
    code = _generate_otp_code()
    expires_at = datetime.utcnow() + timedelta(minutes=5)
    client.otp_code = code
    client.otp_expiry = expires_at
    db.commit()
    send_email_otp(data.email, code)
    return {"status": "sent"}


@app.post("/forgot-password")
def forgot_password(data: EmailOnlyRequest, db: Session = Depends(get_db)):
    """Always returns the same shape; only sends mail for verified accounts."""
    client = db.query(Client).filter(Client.email == data.email).first()
    if client and client.is_verified:
        code = _generate_otp_code()
        expires_at = datetime.utcnow() + timedelta(minutes=5)
        client.password_reset_otp = code
        client.password_reset_otp_expiry = expires_at
        db.commit()
        send_password_reset_email(data.email, code)
    return {"status": "ok"}


@app.post("/reset-password")
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    client = db.query(Client).filter(Client.email == data.email).first()
    if not client or not client.is_verified:
        raise HTTPException(status_code=400, detail="Invalid or expired reset code")
    if not client.password_reset_otp_expiry or client.password_reset_otp_expiry < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired reset code")
    if not client.password_reset_otp or client.password_reset_otp.strip() != data.code.strip():
        raise HTTPException(status_code=400, detail="Invalid or expired reset code")

    client.password = hash_password(data.new_password)
    client.password_reset_otp = None
    client.password_reset_otp_expiry = None
    client.otp_code = None
    client.otp_expiry = None
    db.commit()
    return {"status": "password_updated"}


# ---------------- LOGIN ---------------- #
@app.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    client = db.query(Client).filter(Client.email == data.email.strip().lower()).first()

    if not client or not verify_password(data.password, client.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not client.is_verified:
        raise HTTPException(status_code=403, detail="Please verify your email")

    token = create_access_token({"client_id": str(client.id)})
    return {"access_token": token}


@app.get("/client")
def get_client_data(
    client_id: str = Depends(get_current_client_id),
    db: Session = Depends(get_db),
):
    client = db.query(Client).filter(Client.id == _parse_client_uuid(client_id)).first()

    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    setup_ready = bool(
        (client.calendar_id or "").strip()
        and (client.sheet_id or "").strip()
        and (client.timezone or "").strip()
    )
    return {
        "name": client.name,
        "minutes_used": 0,
        "plan_limit": 1000,
        "calendar_id": client.calendar_id or "",
        "sheet_id": client.sheet_id or "",
        "timezone": client.timezone or "America/New_York",
        "phone_number": client.phone_number or "",
        "client_phone": client.client_phone or "",
        "setup_complete": setup_ready,
        "business_name": client.business_name or "",
        "working_hours": client.working_hours or {},
        "slot_duration": client.slot_duration or 30,
        "services": client.services or [],
        "free_text": client.free_text or "",
    }


# ---------------- SETUP (UPSERT SAME ROW) ---------------- #
@app.post("/setup")
def setup(
    payload: SetupPayload,
    client_id: str = Depends(get_current_client_id),
    db: Session = Depends(get_db),
):
    client = db.query(Client).filter(Client.id == _parse_client_uuid(client_id)).first()

    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    sheet_in = (payload.sheet_id or "").strip() if payload.sheet_id else ""
    if sheet_in:
        try:
            ensure_booking_sheet_headers(sheet_in)
        except Exception as e:
            print("SETUP SHEET HEAL:", repr(e))
            raise HTTPException(status_code=400, detail="Invalid or inaccessible Google Sheet") from e
        client.sheet_id = sheet_in
    elif not (client.sheet_id or "").strip():
        try:
            title = payload.business_name.strip() or (client.name or "Bookings")
            client.sheet_id = create_provisioned_booking_sheet(title)
        except Exception as e:
            print("SHEET PROVISION ERROR:", repr(e))
            raise HTTPException(
                status_code=500,
                detail="Could not create booking sheet. Check Google credentials and Drive/Sheets API access.",
            ) from e
    else:
        try:
            ensure_booking_sheet_headers((client.sheet_id or "").strip())
        except Exception as e:
            print("SETUP SHEET HEAL:", repr(e))
            raise HTTPException(status_code=400, detail="Could not validate booking sheet headers") from e

    client.client_phone = payload.client_phone
    client.calendar_id = payload.calendar_id
    client.timezone = payload.timezone
    client.business_name = payload.business_name
    client.working_hours = payload.working_hours
    client.slot_duration = payload.slot_duration
    client.services = payload.services
    client.free_text = payload.free_text

    db.commit()
    db.refresh(client)

    return {"status": "setup_saved"}


@app.get("/bookings")
def list_bookings(
    client_id: str = Depends(get_current_client_id),
    db: Session = Depends(get_db),
):
    """Booking history for dashboard; empty if integrations are not connected."""
    cid = _parse_client_uuid(client_id)
    client = db.query(Client).filter(Client.id == cid).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    if not ((client.calendar_id or "").strip() and (client.sheet_id or "").strip()):
        return []
    try:
        return list_booking_rows_for_dashboard((client.sheet_id or "").strip())
    except Exception as e:
        print("BOOKINGS READ:", repr(e))
        return []


@app.get("/analytics")
def sheet_analytics(
    client_id: str = Depends(get_current_client_id),
    db: Session = Depends(get_db),
):
    """Live metrics from the tenant's Google Sheet (no PostgreSQL booking storage)."""
    cid = _parse_client_uuid(client_id)
    client = db.query(Client).filter(Client.id == cid).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    tz = (client.timezone or "America/New_York").strip() or "America/New_York"
    integrations_ready = bool((client.calendar_id or "").strip() and (client.sheet_id or "").strip())
    sheet_id = (client.sheet_id or "").strip()
    if not integrations_ready:
        return empty_analytics_payload(
            integrations_ready=False,
            rows_read_ok=False,
            timezone_str=tz,
        )
    try:
        rows = list_booking_rows_for_dashboard(sheet_id, limit=2000)
    except Exception as e:
        print("ANALYTICS READ:", repr(e))
        return empty_analytics_payload(
            integrations_ready=True,
            rows_read_ok=False,
            timezone_str=tz,
        )
    out = compute_sheet_analytics(rows, tz)
    out["integrations_ready"] = True
    out["rows_read_ok"] = True
    return out


@app.patch("/bookings/{row_id}")
def patch_booking_row_endpoint(
    row_id: int,
    payload: BookingPatchRequest,
    client_id: str = Depends(get_current_client_id),
    db: Session = Depends(get_db),
):
    """Update a booking row in the client's Google Sheet (1-based row_id; row 1 is headers)."""
    if row_id < 2:
        raise HTTPException(status_code=400, detail="Invalid row_id")
    client = db.query(Client).filter(Client.id == _parse_client_uuid(client_id)).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    sheet_id = (client.sheet_id or "").strip()
    if not sheet_id:
        raise HTTPException(status_code=400, detail="No booking sheet configured")
    allowed = {"date", "time", "status", "name", "phone", "notes"}
    updates = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if k in allowed}
    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    if "phone" in updates and updates["phone"] is not None:
        try:
            updates["phone"] = normalize_and_validate_phone(str(updates["phone"]))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    if "date" in updates or "time" in updates:
        try:
            cells = get_data_row_cells(sheet_id, row_id)
        except LookupError:
            raise HTTPException(status_code=404, detail="Booking row not found") from None
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e
        merged_date = updates["date"] if "date" in updates else cells[3]
        merged_time = updates["time"] if "time" in updates else cells[4]
        try:
            assert_booking_start_in_future(merged_date, merged_time, client.timezone or "America/New_York")
        except BookingDatetimeError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        patch_booking_data_row(sheet_id, row_id, **updates)
    except LookupError:
        raise HTTPException(status_code=404, detail="Booking row not found") from None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        print("PATCH BOOKING:", repr(e))
        raise HTTPException(status_code=500, detail="Could not update booking") from e
    return {"status": "updated"}


@app.delete("/bookings/{row_id}")
def delete_booking_row_endpoint(
    row_id: int,
    client_id: str = Depends(get_current_client_id),
    db: Session = Depends(get_db),
):
    """Delete a booking row from the client's Google Sheet."""
    if row_id < 2:
        raise HTTPException(status_code=400, detail="Invalid row_id")
    client = db.query(Client).filter(Client.id == _parse_client_uuid(client_id)).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    sheet_id = (client.sheet_id or "").strip()
    if not sheet_id:
        raise HTTPException(status_code=400, detail="No booking sheet configured")
    try:
        get_data_row_cells(sheet_id, row_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="Booking row not found") from None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    try:
        delete_booking_data_row(sheet_id, row_id)
    except Exception as e:
        print("DELETE BOOKING:", repr(e))
        raise HTTPException(status_code=500, detail="Could not delete booking") from e
    return {"status": "deleted"}


@app.post("/check-availability")
def availability(
    req: BookingRequest,
    client_id: str = Depends(get_current_client_id),
    db: Session = Depends(get_db),
):
    try:
        client = db.query(Client).filter(Client.id == _parse_client_uuid(client_id)).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        if req.client_id != client.id:
            raise HTTPException(status_code=400, detail="client_id does not match authenticated session")
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
        client = db.query(Client).filter(Client.id == _parse_client_uuid(client_id)).first()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        if req.client_id != client.id:
            raise HTTPException(status_code=400, detail="client_id does not match authenticated session")
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
            db=db,
        )

    except HTTPException:
        raise
    except Exception as e:
        print("Booking Error:", repr(e))
        raise HTTPException(status_code=500, detail="Booking failed")


@app.post("/book")
def book_create(
    req: BookingRequest,
    background_tasks: BackgroundTasks,
    client_id: str = Depends(get_current_client_id),
    db: Session = Depends(get_db),
):
    """Same as POST /book-appointment: creates calendar event and appends to Google Sheet."""
    return book_web(req, background_tasks, client_id, db)


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
    calendar_id = client.calendar_id
    timezone = client.timezone or "America/New_York"

    date = _vapi_str(payload, "date")
    time = _vapi_str(payload, "time")

    return check_availability_logic(
        date=date,
        time=time,
        calendar_id=calendar_id,
        timezone_str=timezone,
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
        calendar_id = client.calendar_id
        sheet_id = client.sheet_id
        timezone = client.timezone or "America/New_York"

        name = _vapi_str(payload, "name")
        phone = _vapi_str(payload, "phone")
        date = _vapi_str(payload, "date")
        time = _vapi_str(payload, "time")
        notes_raw = payload.get("notes")
        notes = str(notes_raw).strip()[:4000] if notes_raw is not None else ""

        return book_appointment_logic(
            client_id=client.id,
            name=name,
            phone=phone,
            date=date,
            time=time,
            calendar_id=calendar_id,
            sheet_id=sheet_id,
            timezone_str=timezone,
            duration_minutes=_client_slot_minutes(client),
            background_tasks=background_tasks,
            db=db,
            source="vapi",
            notes=notes,
        )

    except HTTPException:
        raise
    except Exception as e:
        print("VAPI Booking Error:", repr(e))
        raise HTTPException(status_code=500, detail="Booking failed")
