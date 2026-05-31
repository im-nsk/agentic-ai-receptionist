"""VAPI tool result string formatting."""

from backend.services.vapi_tool_response import (
    build_unavailable_speech,
    format_vapi_tool_result,
)


def test_format_uses_assistant_should_say():
    s = format_vapi_tool_result(
        {
            "not_a_system_error": True,
            "assistant_should_say": "We are closed on Sundays. Would Monday work?",
        }
    )
    assert "SCHEDULING" in s
    assert "Sunday" in s
    assert "\n" not in s


def test_book_not_booked_not_failed_json():
    s = format_vapi_tool_result(
        {
            "status": "not_booked",
            "not_a_system_error": True,
            "assistant_should_say": "That Sunday is not available. Would Monday at 9 AM work?",
        }
    )
    assert "failed" not in s.lower() or "system error" in s.lower()
    assert "Monday" in s


def test_closed_day_speech():
    from backend.services.tenant_resolver import TenantContext
    import uuid

    tenant = TenantContext(
        client_id=uuid.uuid4(),
        inbound_number="+1",
        match_field="test",
        business_name="Wrixio",
        calendar_id="c",
        sheet_id="s",
        timezone="America/New_York",
        business_prompt="",
        slot_duration=30,
        weekly_availability={
            "monday": {"enabled": True, "start": "09:00", "end": "17:00"},
            "tuesday": {"enabled": True, "start": "09:00", "end": "17:00"},
            "wednesday": {"enabled": True, "start": "09:00", "end": "17:00"},
            "thursday": {"enabled": True, "start": "09:00", "end": "17:00"},
            "friday": {"enabled": True, "start": "09:00", "end": "17:00"},
            "saturday": {"enabled": False, "start": "09:00", "end": "17:00"},
            "sunday": {"enabled": False, "start": "09:00", "end": "17:00"},
        },
        blocked_dates=[],
        working_hours=None,
        services=None,
        twilio_number="+1",
        client_phone="",
        owner_email="",
    )
    # 2026-05-24 is a Sunday
    speech = build_unavailable_speech(tenant, "2026-05-24", "10:00 AM")
    assert speech["reason_code"] == "closed_day"
    assert "Sunday" in speech["assistant_should_say"]
