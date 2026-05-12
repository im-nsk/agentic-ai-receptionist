import uuid

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from backend.db.database import Base


class Client(Base):
    __tablename__ = "clients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    name = Column(String)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)

    phone_number = Column(String, unique=True, index=True)
    client_phone = Column(String)

    calendar_id = Column(String)
    sheet_id = Column(String)
    timezone = Column(String)

    business_name = Column(String)
    working_hours = Column(JSONB)
    weekly_availability = Column(JSONB)
    blocked_dates = Column(JSONB)
    slot_duration = Column(Integer)
    services = Column(JSONB)
    free_text = Column(Text)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

    otp_code = Column(Text)
    otp_expiry = Column(DateTime)
    is_verified = Column(Boolean, nullable=False, default=False)

    password_reset_otp = Column(Text)
    password_reset_otp_expiry = Column(DateTime)

    def __repr__(self):
        return f"<Client {self.email}>"
