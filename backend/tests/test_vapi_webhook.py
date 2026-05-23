"""Unit tests for VAPI webhook routing (no DB)."""

from backend.services.vapi_webhook import (
    _detect_intent,
    _iter_tool_calls,
    _tool_args,
)
from backend.services.vapi_payload import (
    is_manual_flat_test_payload,
    is_vapi_tool_calls_envelope,
)


def test_tool_calls_detection():
    body = {"message": {"type": "tool-calls", "toolCallList": []}}
    assert is_vapi_tool_calls_envelope(body) is True
    assert is_manual_flat_test_payload(body) is False


def test_iter_tool_calls():
    msg = {
        "toolCallList": [
            {"id": "tc1", "name": "book_appointment", "arguments": {"date": "2026-05-21"}},
        ],
    }
    calls = _iter_tool_calls(msg)
    assert len(calls) == 1
    assert _tool_args(calls[0])["date"] == "2026-05-21"


def test_intent_aliases():
    assert _detect_intent("book_appointment") == "book_appointment"
    assert _detect_intent("check-availability") == "check_availability"
