"""TwiML helpers for inbound Twilio voice webhooks."""

from __future__ import annotations

import xml.sax.saxutils as xml_escape

from backend.services.tenant_resolver import TenantContext


def _say(message: str) -> str:
    safe = xml_escape.escape(message)
    return f"<Say>{safe}</Say>"


def twiml_no_tenant_configured(inbound_to: str) -> str:
    print(
        "TWILIO_VOICE:",
        "no tenant for inbound To",
        f"to={inbound_to!r}",
        "responding=unconfigured",
    )
    body = (
        "Sorry, this phone line is not set up yet. "
        "Please try again later or contact the business directly."
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f"{_say(body)}"
        "<Hangup/>"
        "</Response>"
    )


def twiml_tenant_greeting(tenant: TenantContext, caller_from: str) -> str:
    name = tenant.business_name or "our office"
    print(
        "TWILIO_VOICE:",
        "tenant greeting",
        f"to={tenant.inbound_number!r}",
        f"from={caller_from!r}",
        tenant.log_fields(),
    )
    body = f"Thank you for calling {name}. One moment please."
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f"{_say(body)}"
        "<Pause length=\"1\"/>"
        f"{_say('Please hold while we connect you.')}"
        "<Hangup/>"
        "</Response>"
    )
