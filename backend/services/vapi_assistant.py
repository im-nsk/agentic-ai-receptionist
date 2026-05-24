"""Dynamic per-call VAPI assistant configuration (multi-tenant)."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from backend.services.tenant_resolver import TenantContext

# Generic layer only — no clinic/business names (tenant context injected per call).
_GENERIC_BASE_INSTRUCTIONS = """You are a professional AI phone receptionist.

Rules:
- Represent ONLY the business described in the Business Context section below.
- Never mention clinics, hospitals, or other businesses unless the business context says so.
- Be warm, concise, and natural on the phone.
- For scheduling: always call check_availability before book_appointment.
- If check_availability returns slot_unavailable or available=false, that is NORMAL — suggest alternative_slots from the tool response. Never call it a technical error, system failure, or bug.
- If availability_check_failed is true, you may still suggest alternatives but mention you are checking the schedule.
- Collect the caller's name, phone number, preferred date, and time before booking.
- When calling tools, use date as YYYY-MM-DD when possible (example: 2026-05-25) and time like 2:30 PM.
- The server resolves which business to use from the phone call; you do not need to pass to_number in tools unless the tool schema requires it.
"""

_BOOKING_WORKFLOW = """
Booking workflow:
1. Greet the caller using the business name.
2. Ask what they need (appointment, hours, services).
3. For appointments: ask date and time, then call check_availability.
4. If unavailable, read alternative_slots and ask which they prefer; check again if needed.
5. When a slot is available, confirm name and phone, then call book_appointment.
6. Confirm the booking aloud after book_appointment returns status confirmed.
"""


def _services_summary(services: Any) -> str:
    if not services:
        return ""
    if isinstance(services, list):
        parts: List[str] = []
        for item in services[:25]:
            if isinstance(item, dict):
                name = str(item.get("name") or item.get("title") or "").strip()
                if name:
                    parts.append(name)
            elif item:
                parts.append(str(item).strip())
        return ", ".join(p for p in parts if p)
    if isinstance(services, dict):
        return ", ".join(str(k) for k in list(services.keys())[:25])
    return str(services).strip()[:500]


def build_system_prompt(tenant: TenantContext) -> str:
    sections = [_GENERIC_BASE_INSTRUCTIONS.strip(), ""]
    sections.append("## Business context")
    sections.append(f"Business name: {tenant.business_name or 'our business'}")
    sections.append(f"Timezone: {tenant.timezone}")
    if tenant.business_prompt:
        sections.append("")
        sections.append("### Owner instructions")
        sections.append(tenant.business_prompt.strip())
    svc = _services_summary(tenant.services)
    if svc:
        sections.append("")
        sections.append("### Services")
        sections.append(svc)
    sections.append(_BOOKING_WORKFLOW.strip())
    return "\n".join(sections).strip()


def build_first_message(tenant: TenantContext) -> str:
    name = (tenant.business_name or "our office").strip()
    return (
        os.getenv("VAPI_FIRST_MESSAGE_TEMPLATE")
        or "Thank you for calling {{business_name}}. How can I help you today?"
    ).replace("{{business_name}}", name)


def build_assistant_request_response(tenant: TenantContext) -> Dict[str, Any]:
    """
    VAPI ``assistant-request`` server URL response.

    Uses VAPI_BASE_ASSISTANT_ID + assistantOverrides when set (recommended).
    Otherwise returns a minimal inline ``assistant`` object (voice/model from env).
    """
    system_prompt = build_system_prompt(tenant)
    first_message = build_first_message(tenant)
    base_assistant_id = (os.getenv("VAPI_BASE_ASSISTANT_ID") or "").strip()

    variable_values = {
        "business_name": tenant.business_name or "",
        "business_prompt": tenant.business_prompt or "",
        "timezone": tenant.timezone,
        "client_id": str(tenant.client_id),
        "inbound_twilio_number": tenant.inbound_number or tenant.twilio_number or "",
        "services_summary": _services_summary(tenant.services),
    }

    print(
        "[VAPI BUSINESS PROMPT]",
        f"business_name={tenant.business_name!r}",
        f"prompt_len={len(tenant.business_prompt or '')}",
        f"has_services={bool(_services_summary(tenant.services))}",
    )
    base_id_log = base_assistant_id if base_assistant_id else "(inline assistant)"
    print(
        "[VAPI ASSISTANT OVERRIDE]",
        f"base_assistant_id={base_id_log!r}",
        f"first_message={first_message[:120]!r}",
        f"system_prompt_preview={system_prompt[:400]!r}...",
    )

    overrides: Dict[str, Any] = {
        "firstMessage": first_message,
        "variableValues": variable_values,
        "model": {
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt,
                }
            ],
        },
    }

    if base_assistant_id:
        response: Dict[str, Any] = {
            "assistantId": base_assistant_id,
            "assistantOverrides": overrides,
        }
    else:
        model_provider = (os.getenv("VAPI_MODEL_PROVIDER") or "openai").strip()
        model_name = (os.getenv("VAPI_MODEL_NAME") or "gpt-4o").strip()
        voice_provider = (os.getenv("VAPI_VOICE_PROVIDER") or "11labs").strip()
        voice_id = (os.getenv("VAPI_VOICE_ID") or "").strip()

        assistant: Dict[str, Any] = {
            "name": f"{tenant.business_name or 'Business'} Receptionist",
            "firstMessage": first_message,
            "model": {
                "provider": model_provider,
                "model": model_name,
                "messages": overrides["model"]["messages"],
            },
        }
        if voice_id:
            assistant["voice"] = {"provider": voice_provider, "voiceId": voice_id}
        response = {"assistant": assistant}

    print(
        "[VAPI SESSION CONFIG]",
        json.dumps(
            {
                "client_id": str(tenant.client_id),
                "business_name": tenant.business_name,
                "timezone": tenant.timezone,
                "match_field": tenant.match_field,
                "mode": "assistantId+overrides" if base_assistant_id else "inline_assistant",
            },
            default=str,
        ),
    )
    return response


def build_assistant_request_fallback(*, reason: str) -> Dict[str, Any]:
    """When tenant cannot be resolved — generic assistant, no clinic branding."""
    print("[VAPI SESSION CONFIG]", "FAILED", f"reason={reason!r}")
    msg = (
        "Thank you for calling. Our system could not identify this business line. "
        "Please try again later or contact support."
    )
    base_id = (os.getenv("VAPI_BASE_ASSISTANT_ID") or "").strip()
    system = (
        "You are a phone receptionist. The business could not be loaded. "
        "Apologize briefly and ask the caller to try again later."
    )
    if base_id:
        return {
            "assistantId": base_id,
            "assistantOverrides": {
                "firstMessage": msg,
                "model": {"messages": [{"role": "system", "content": system}]},
            },
        }
    return {
        "assistant": {
            "firstMessage": msg,
            "model": {
                "provider": os.getenv("VAPI_MODEL_PROVIDER") or "openai",
                "model": os.getenv("VAPI_MODEL_NAME") or "gpt-4o",
                "messages": [{"role": "system", "content": system}],
            },
        }
    }
