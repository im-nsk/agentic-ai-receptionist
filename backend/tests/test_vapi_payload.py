"""Unit tests for VAPI payload parsing (no DB)."""

from backend.services.vapi_payload import (
    extract_inbound_to_candidates,
    is_flat_tool_args_with_call_context,
    is_manual_flat_test_payload,
    is_vapi_tool_calls_envelope,
    normalize_vapi_body,
    split_root_flat_tool_body,
)


def test_tool_calls_envelope():
    body = {
        "message": {
            "type": "tool-calls",
            "toolCallList": [{"id": "1", "name": "book", "arguments": {}}],
            "phoneNumber": {"twilioPhoneNumber": "+15551234567"},
            "call": {"id": "call-1", "customer": {"number": "+15559876543"}},
        }
    }
    assert is_vapi_tool_calls_envelope(body) is True
    assert is_manual_flat_test_payload(body) is False
    _, msg = normalize_vapi_body(body)
    cands = extract_inbound_to_candidates(body, msg)
    assert any("+15551234567" in p for _, p in cands)


def test_root_level_tool_calls():
    body = {
        "type": "tool-calls",
        "toolCallList": [],
        "phoneNumber": {"number": "+15550001111"},
    }
    assert is_vapi_tool_calls_envelope(body) is True
    _, msg = normalize_vapi_body(body)
    assert msg.get("type") == "tool-calls"


def test_flat_book_misroute_not_tool_calls():
    body = {"name": "Jane", "date": "2026-05-21", "time": "10:00", "phone": "+15559876543"}
    assert is_vapi_tool_calls_envelope(body) is False
    assert is_manual_flat_test_payload(body) is True


def test_flat_with_message_wrapper_not_legacy():
    body = {
        "message": {"type": "tool-calls", "toolCallList": []},
        "name": "Jane",
    }
    assert is_manual_flat_test_payload(body) is False


def test_flat_tool_args_with_call_context():
    body = {
        "name": "Jane",
        "date": "2026-05-21",
        "time": "10:00",
        "phone": "+15559876543",
        "call": {"id": "c1", "customer": {"number": "+15559876543"}},
        "phoneNumber": {"twilioPhoneNumber": "+15551234567"},
    }
    assert is_flat_tool_args_with_call_context(body) is True
    assert is_manual_flat_test_payload(body) is False
    args, msg = split_root_flat_tool_body(body)
    assert args["name"] == "Jane"
    assert msg["phoneNumber"]["twilioPhoneNumber"] == "+15551234567"
    cands = extract_inbound_to_candidates(body, msg, args)
    assert any("+15551234567" in p for _, p in cands)
