"""Short human-readable booking references for sheet + phone use (not UUIDs)."""

from __future__ import annotations

import re
import secrets
from typing import Optional


def generate_human_booking_id(business_name: Optional[str]) -> str:
    """
    Prefix (2 letters from business name, or 'ar') + hyphen + 4 digits (1000–9999).
    Example: wx-4821, ar-5932
    """
    raw = re.sub(r"[^a-zA-Z0-9]", "", (business_name or "").strip().lower())
    if len(raw) >= 2:
        prefix = raw[:2]
    elif len(raw) == 1:
        prefix = raw + "x"
    else:
        prefix = "ar"
    num = secrets.randbelow(9000) + 1000
    return f"{prefix}-{num}"
