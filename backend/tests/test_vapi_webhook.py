"""Unit tests for VAPI tool-calls routing (no DB)."""

from backend.services.vapi_webhook import (
    _detect_intent,
    _iter_tool_calls,
    _tool_args,
    is_legacy_flat_booking_payload,
    is_vapi_tool_calls_payload,
)


def test_tool_calls_detection():
    body = {"message": {"type": "tool-calls", "toolCallList": []}}
    assert is_vapi_tool_calls_payload(body) is True
    assert is_legacy_flat_booking_payload(body) is False


def test_legacy_flat_detection():
    body = {"to_number": "+1", "name": "A", "date": "2026-05-21", "time": "10:00"}
    assert is_legacy_flat_booking_payload(body) is True
    assert is_vapi_tool_calls_payload(body) is False


def test_iter_tool_calls():
    msg = {
        "toolCallList": [
            {"id": "tc1", "name": "book_appointment", "arguments": {"date": "2026-05-21"}},
        ],
    }
    calls = _iter_tool_calls(msg)
    assert len(calls) == 1
    assert calls[0]["id"] == "tc1"
    assert _tool_args(calls[0])["date"] == "2026-05-21"


def test_intent_aliases():
    assert _detect_intent("book_appointment") == "book_appointment"
    assert _detect_intent("check-availability") == "check_availability"
    assert _detect_intent("unknown_tool") == "unknown:unknown_tool"
