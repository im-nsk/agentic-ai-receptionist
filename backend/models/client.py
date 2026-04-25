from sqlalchemy import Column, String, Integer
from backend.db.database import Base
import uuid

class Client(Base):
    __tablename__ = "clients"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String)
    email = Column(String, unique=True)
    password = Column(String)

    calendar_id = Column(String)
    sheet_id = Column(String)
    phone = Column(String)

    # 🔥 ADD THIS
    timezone = Column(String, default="America/New_York")

    # Usage tracking
    minutes_used = Column(Integer, default=0)
    plan_limit = Column(Integer, default=1000)