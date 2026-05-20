"""Resolve inbound call/SMS routing to a tenant Client by Twilio number (multi-tenant)."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Any, List, Optional

from sqlalchemy.orm import Session

from backend.models.client import Client
from backend.services.phone_validation import normalize_and_validate_phone


@dataclass(frozen=True)
class TenantContext:
    """Per-tenant config loaded from DB for voice/VAPI/booking (no global business config)."""

    client_id: uuid.UUID
    inbound_number: str
    match_field: str
    business_name: str
    calendar_id: str
    sheet_id: str
    timezone: str
    business_prompt: str
    slot_duration: int
    weekly_availability: Any
    blocked_dates: Any
    working_hours: Any
    services: Any
    twilio_number: str
    client_phone: str
    owner_email: str

    @classmethod
    def from_client(
        cls,
        client: Client,
        *,
        inbound_number: str,
        match_field: str,
    ) -> "TenantContext":
        slot = client.slot_duration or 30
        return cls(
            client_id=client.id,
            inbound_number=inbound_number,
            match_field=match_field,
            business_name=(client.business_name or client.name or "").strip(),
            calendar_id=(client.calendar_id or "").strip(),
            sheet_id=(client.sheet_id or "").strip(),
            timezone=(client.timezone or "America/New_York").strip() or "America/New_York",
            business_prompt=(client.free_text or "").strip(),
            slot_duration=int(slot) if slot and int(slot) > 0 else 30,
            weekly_availability=client.weekly_availability,
            blocked_dates=client.blocked_dates,
            working_hours=client.working_hours,
            services=client.services,
            twilio_number=(client.twilio_number or "").strip(),
            client_phone=(client.client_phone or "").strip(),
            owner_email=(client.email or "").strip(),
        )

    def log_fields(self) -> dict:
        return {
            "client_id": str(self.client_id),
            "match_field": self.match_field,
            "inbound_to": self.inbound_number,
            "business_name": self.business_name,
            "calendar_id": self.calendar_id or None,
            "sheet_id": self.sheet_id or None,
            "timezone": self.timezone,
            "has_business_prompt": bool(self.business_prompt),
        }


def normalize_inbound_phone(raw: Optional[str]) -> Optional[str]:
    """Normalize Twilio To/From to E.164 when possible."""
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    try:
        return normalize_and_validate_phone(s)
    except ValueError:
        digits = re.sub(r"\D", "", s)
        if len(digits) < 10:
            return None
        return f"+{digits}" if s.startswith("+") else digits


def _lookup_candidates(normalized: str) -> List[str]:
    candidates: List[str] = [normalized]
    digits = re.sub(r"\D", "", normalized)
    if digits and digits not in candidates:
        candidates.append(digits)
    if not normalized.startswith("+") and digits:
        plus = f"+{digits}"
        if plus not in candidates:
            candidates.append(plus)
    return candidates


def resolve_client_by_inbound_number(
    db: Session,
    to_number: Optional[str],
    *,
    log_prefix: str = "TENANT",
) -> Optional[TenantContext]:
    """
    Map inbound Twilio/VAPI ``To`` number → tenant Client.

    Lookup order (scalable: one twilio_number → one client):
      1. ``clients.twilio_number`` (preferred)
      2. ``clients.phone_number`` (legacy during migration)
    """
    normalized = normalize_inbound_phone(to_number)
    if not normalized:
        print(f"{log_prefix} lookup skipped: empty or invalid To={to_number!r}")
        return None

    candidates = _lookup_candidates(normalized)
    print(f"{log_prefix} lookup:", f"raw_to={to_number!r}", f"candidates={candidates!r}")

    client = (
        db.query(Client)
        .filter(Client.twilio_number.in_(candidates))
        .first()
    )
    match_field = "twilio_number"
    if not client:
        client = (
            db.query(Client)
            .filter(Client.phone_number.in_(candidates))
            .first()
        )
        match_field = "phone_number" if client else ""

    if not client:
        print(f"{log_prefix} NO MATCH for inbound To={normalized!r}")
        return None

    ctx = TenantContext.from_client(
        client,
        inbound_number=normalized,
        match_field=match_field,
    )
    print(f"{log_prefix} MATCHED:", ctx.log_fields())
    return ctx


def assign_twilio_number_to_client(
    db: Session,
    *,
    client_id: uuid.UUID,
    twilio_number: str,
) -> Client:
    """Assign the shared Twilio inbound number to exactly one client."""
    normalized = normalize_inbound_phone(twilio_number)
    if not normalized:
        raise ValueError("Invalid Twilio number.")

    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise ValueError("Client not found.")

    db.query(Client).filter(
        Client.twilio_number.in_(_lookup_candidates(normalized)),
        Client.id != client_id,
    ).update({Client.twilio_number: None}, synchronize_session=False)

    client.twilio_number = normalized
    db.commit()
    db.refresh(client)
    print(
        "TWILIO_ASSIGN:",
        f"client_id={client_id}",
        f"twilio_number={normalized!r}",
        f"email={client.email!r}",
    )
    return client
