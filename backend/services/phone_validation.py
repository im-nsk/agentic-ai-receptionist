"""Shared phone validation for web, VAPI, setup, and sheet patches."""

from __future__ import annotations

import re
from typing import Optional

_ALLOWED_BODY = re.compile(r"^[\d\s\-\+\(\)\.]+$")


def normalize_and_validate_phone(raw: Optional[str]) -> str:
    """
    Accept E.164 (+ and 10–15 digits) or 10–15 digits with common separators.
    Returns a normalized string (+digits when input had a leading +, else digits only).
    """
    if raw is None:
        raise ValueError("Phone number is required.")
    s = str(raw).strip()
    if not s:
        raise ValueError("Phone number is required.")
    if re.search(r"[A-Za-z]", s):
        raise ValueError("Phone numbers can only include digits and common separators (+, spaces, dashes, parentheses).")
    if not _ALLOWED_BODY.fullmatch(s):
        raise ValueError("Phone number contains invalid characters.")
    digits = re.sub(r"\D", "", s)
    if len(digits) < 10:
        raise ValueError("Phone number is too short — use at least 10 digits (include country code).")
    if len(digits) > 15:
        raise ValueError("Phone number is too long — international numbers allow at most 15 digits after +.")
    if s.strip().startswith("+"):
        return f"+{digits}"
    return digits
