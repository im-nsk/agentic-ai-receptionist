import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.services.phone_validation import normalize_and_validate_phone


class AvailabilityCheckRequest(BaseModel):
    """Lightweight body for /check-availability (ignores legacy booking fields)."""

    model_config = ConfigDict(extra="ignore")

    date: str
    time: str
    client_id: Optional[uuid.UUID] = None
    name: Optional[str] = None
    phone: Optional[str] = None

    @field_validator("date", "time")
    @classmethod
    def _strip_datetime_fields(cls, value: str) -> str:
        return value.strip()


class BookingRequest(BaseModel):
    client_id: uuid.UUID
    name: str = Field(..., min_length=2)
    phone: str
    date: str
    time: str

    @field_validator("phone")
    @classmethod
    def _validate_phone(cls, value: str) -> str:
        return normalize_and_validate_phone(value)

    @field_validator("date", "time")
    @classmethod
    def _strip_datetime_fields(cls, value: str) -> str:
        return value.strip()