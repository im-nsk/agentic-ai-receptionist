"""Dynamic per-call VAPI assistant configuration (multi-tenant)."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List

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
- Do NOT pass to_number in tools — the server identifies the business from the phone call automatically. Ignore empty or "Restricted" to_number values.
- Tool results are plain English sentences. Read them aloud naturally. If the result says SCHEDULING (not a system error), never apologize for a technical problem.
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

_ASSISTANT_REQUEST_TYPES = frozenset(
    {
        "assistant-request",
        "assistantrequest",
        "assistant_request",
    }
)


def is_assistant_request_message_type(msg_type: str) -> bool:
    return (msg_type or "").strip().lower().replace("_", "-") in _ASSISTANT_REQUEST_TYPES


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


def _use_inline_assistant_response() -> bool:
    """
    When true (default), return a full ``assistant`` object so VAPI cannot keep
    the published dashboard system prompt (e.g. "clinic receptionist").

    Set VAPI_USE_INLINE_ASSISTANT=false to use assistantId + assistantOverrides merge only.
    """
    return os.getenv("VAPI_USE_INLINE_ASSISTANT", "true").strip().lower() in (
        "true",
        "1",
        "yes",
        "on",
    )


def _build_inline_assistant(
    tenant: TenantContext,
    system_prompt: str,
    first_message: str,
) -> Dict[str, Any]:
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
            "messages": [{"role": "system", "content": system_prompt}],
        },
    }
    if voice_id:
        assistant["voice"] = {"provider": voice_provider, "voiceId": voice_id}
    return assistant


def _log_dynamic_assistant_built(
    tenant: TenantContext,
    *,
    system_prompt: str,
    first_message: str,
    response_mode: str,
    base_assistant_id: str,
) -> None:
    biz = (tenant.business_prompt or "").strip()
    print(
        "[VAPI BUSINESS PROMPT]",
        f"business_name={tenant.business_name!r}",
        f"prompt_len={len(biz)}",
        f"preview={biz[:400]!r}" if biz else "preview=(empty)",
    )
    print("[VAPI SYSTEM PROMPT PREVIEW]", system_prompt[:800])
    print("[VAPI FIRST MESSAGE]", first_message)
    print(
        "[VAPI ASSISTANT OVERRIDE]",
        f"mode={response_mode!r}",
        f"base_assistant_id={base_assistant_id or '(none)'}",
        f"client_id={tenant.client_id}",
        f"match_field={tenant.match_field!r}",
    )


def build_dynamic_assistant(tenant: TenantContext) -> Dict[str, Any]:
    """
    Build VAPI ``assistant-request`` response for one tenant.

    VAPI only applies this when:
    - Phone number has NO fixed assistantId (sends assistant-request to server URL), OR
    - Squad/workflow routes through server URL.

    If callers still hear the dashboard "clinic" prompt, check logs for
    ``[VAPI ASSISTANT REQUEST RECEIVED]`` — if missing, only tool-calls run and
    the published assistant is used unchanged.
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

    use_inline = _use_inline_assistant_response()

    if use_inline:
        response: Dict[str, Any] = {
            "assistant": _build_inline_assistant(tenant, system_prompt, first_message),
        }
        response_mode = "inline_assistant (full replace)"
    elif base_assistant_id:
        response = {
            "assistantId": base_assistant_id,
            "assistantOverrides": {
                "firstMessage": first_message,
                "variableValues": variable_values,
                "model": {
                    "provider": (os.getenv("VAPI_MODEL_PROVIDER") or "openai").strip(),
                    "model": (os.getenv("VAPI_MODEL_NAME") or "gpt-4o").strip(),
                    "messages": [{"role": "system", "content": system_prompt}],
                },
            },
        }
        response_mode = "assistantId+assistantOverrides"
    else:
        response = {
            "assistant": _build_inline_assistant(tenant, system_prompt, first_message),
        }
        response_mode = "inline_assistant (no base id)"

    _log_dynamic_assistant_built(
        tenant,
        system_prompt=system_prompt,
        first_message=first_message,
        response_mode=response_mode,
        base_assistant_id=base_assistant_id,
    )

    print(
        "[VAPI SESSION CONFIG]",
        json.dumps(
            {
                "response_mode": response_mode,
                "client_id": str(tenant.client_id),
                "business_name": tenant.business_name,
                "has_business_prompt": bool(tenant.business_prompt),
            },
            default=str,
        ),
    )
    print(
        "[VAPI ASSISTANT RESPONSE OUT]",
        json.dumps(response, default=str)[:1500],
    )
    return response


def build_assistant_request_response(tenant: TenantContext) -> Dict[str, Any]:
    """Alias for ``build_dynamic_assistant`` (legacy name)."""
    return build_dynamic_assistant(tenant)


def build_assistant_request_fallback(*, reason: str) -> Dict[str, Any]:
    """When tenant cannot be resolved — generic assistant, no clinic branding."""
    print("[VAPI SESSION CONFIG]", "FAILED", f"reason={reason!r}")
    msg = (
        "Thank you for calling. Our system could not identify this business line. "
        "Please try again later or contact support."
    )
    system = (
        "You are a phone receptionist. The business could not be loaded. "
        "Apologize briefly and ask the caller to try again later."
    )
    print("[VAPI SYSTEM PROMPT PREVIEW]", system[:400])
    print("[VAPI FIRST MESSAGE]", msg)

    if _use_inline_assistant_response():
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

    base_id = (os.getenv("VAPI_BASE_ASSISTANT_ID") or "").strip()
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
