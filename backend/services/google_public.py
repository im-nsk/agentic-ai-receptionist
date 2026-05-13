"""Non-secret Google integration metadata for clients (no credentials)."""

from __future__ import annotations

import json
import os
from typing import Optional


def get_booking_service_account_email() -> Optional[str]:
    """
    Email clients must share their calendar with.
    Prefer explicit GOOGLE_SERVICE_ACCOUNT_EMAIL; otherwise parse client_email from GOOGLE_CREDENTIALS_JSON.
    """
    explicit = (os.getenv("GOOGLE_SERVICE_ACCOUNT_EMAIL") or "").strip()
    if explicit:
        return explicit
    raw = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if not raw or not raw.strip():
        return None
    try:
        info = json.loads(raw)
        email = info.get("client_email")
        return email.strip() if isinstance(email, str) and email.strip() else None
    except (json.JSONDecodeError, TypeError, AttributeError):
        return None
