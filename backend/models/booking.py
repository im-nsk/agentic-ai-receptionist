from pydantic import BaseModel, Field, field_validator

from backend.services.phone_validation import normalize_and_validate_phone


class BookingRequest(BaseModel):
    client_id: str
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