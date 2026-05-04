"""
Client model for multi-tenant SaaS.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from backend.db.database import Base


class Client(Base):
    __tablename__ = "clients"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    password = Column(String, nullable=False)

    email_verified = Column(Boolean, default=False, nullable=False)

    phone_number = Column(String, nullable=True, index=True)
    client_phone = Column(String, nullable=True)

    calendar_id = Column(String, nullable=True)
    sheet_id = Column(String, nullable=True)

    timezone = Column(String, default="America/New_York")

    business_name = Column(String, nullable=True)
    working_hours = Column(String, nullable=True)
    slot_duration = Column(Integer, nullable=True, default=30)
    services_json = Column(Text, nullable=True)
    free_text = Column(Text, nullable=True)

    minutes_used = Column(Integer, default=0)
    plan_limit = Column(Integer, default=1000)

    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Client {self.email}>"
