"""Parse Google API client errors into short, log-friendly messages."""

from __future__ import annotations

import json
from typing import Any, Optional

from googleapiclient.errors import HttpError


def google_http_error_message(exc: HttpError) -> str:
    """Best-effort message from a Calendar/Sheets REST HttpError body."""
    try:
        if exc.content:
            payload = json.loads(exc.content.decode("utf-8"))
            err = payload.get("error")
            if isinstance(err, dict):
                msg = err.get("message")
                if isinstance(msg, str) and msg.strip():
                    return msg.strip()
    except Exception:
        pass
    return str(exc).strip() or "Google API error"


def google_http_status(exc: HttpError) -> int:
    return int(getattr(exc.resp, "status", 0) or 0)


def gspread_api_error_message(exc: Exception) -> str:
    """Message from gspread APIError when available."""
    response: Any = getattr(exc, "response", None)
    if response is not None:
        try:
            data = response.json()
            err = data.get("error") if isinstance(data, dict) else None
            if isinstance(err, dict):
                msg = err.get("message")
                if isinstance(msg, str) and msg.strip():
                    return msg.strip()
        except Exception:
            pass
    text = str(exc).strip()
    return text or "Google Sheets API error"
