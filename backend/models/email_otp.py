"""Short-lived signup verification codes (mock email for MVP — code also logged server-side)."""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, String

from backend.db.database import Base


class EmailOTP(Base):
    __tablename__ = "email_otps"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    code = Column(String(6), nullable=False)
    expires_at = Column(DateTime, nullable=False)

    def __repr__(self):
        return f"<EmailOTP {self.email}>"
