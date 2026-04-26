"""
models/client.py

Client model for multi-tenant SaaS system.
Represents each business/customer using the AI receptionist.
"""

from sqlalchemy import Column, String, Integer, DateTime
from backend.db.database import Base
import uuid
from datetime import datetime


class Client(Base):
    __tablename__ = "clients"

    # 🔑 Primary identifier (UUID)
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # 👤 Basic Info
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    password = Column(String, nullable=False)

    # 📞 Contact (optional but useful for future features)
    phone = Column(String, nullable=True)

    # 🗓️ Integrations
    calendar_id = Column(String, nullable=True)   # Google Calendar
    sheet_id = Column(String, nullable=True)      # Google Sheets

    # 🌍 Timezone (important for scheduling logic)
    timezone = Column(String, default="America/New_York")

    # 📊 Usage Tracking
    minutes_used = Column(Integer, default=0)
    plan_limit = Column(Integer, default=1000)

    # 🕒 Metadata
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Client {self.email}>"