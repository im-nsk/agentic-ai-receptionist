"""Persistent booking rows for dashboard (source of truth: backend DB)."""

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID

from backend.db.database import Base


class BookingRecord(Base):
    __tablename__ = "bookings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(Text, nullable=False)
    phone = Column(Text, nullable=False)
    date = Column(Text, nullable=False)
    time = Column(Text, nullable=False)
    status = Column(String(32), nullable=False)

    created_at = Column(DateTime, nullable=False)
