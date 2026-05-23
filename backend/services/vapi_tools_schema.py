"""VAPI custom tool definitions (documentation + GET /vapi/tools/schema)."""

from __future__ import annotations

import os
from typing import Any, Dict, List

from backend.services.voice_datetime import VAPI_TOOL_DATE_PARAM_HINT, VAPI_TOOL_TIME_PARAM_HINT


def public_api_base_url() -> str:
    return (
        os.getenv("PUBLIC_API_URL")
        or os.getenv("RENDER_EXTERNAL_URL")
        or "https://YOUR_BACKEND_HOST"
    ).rstrip("/")


def vapi_tool_definitions() -> List[Dict[str, Any]]:
    """
    Recommended VAPI dashboard tool config.

    Use ONE server URL on the phone number (POST /vapi/webhook) for all tools.
    Do NOT point tools at GET URLs. Method must be POST.
    """
    base = public_api_base_url()
    server_url = f"{base}/vapi/webhook"
    return [
        {
            "type": "function",
            "function": {
                "name": "check_availability",
                "description": (
                    "Check if an appointment slot is open. Always call this before booking. "
                    "If unavailable, read alternative_slots and voice_instruction from the response — "
                    "never tell the caller there is a technical error."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date": {
                            "type": "string",
                            "description": VAPI_TOOL_DATE_PARAM_HINT,
                        },
                        "time": {
                            "type": "string",
                            "description": VAPI_TOOL_TIME_PARAM_HINT,
                        },
                    },
                    "required": ["date", "time"],
                },
            },
            "async": False,
            "server": {
                "url": server_url,
                "method": "POST",
                "headers": {
                    "x-api-key": "USE_RENDER_ENV_VAPI_API_KEY",
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "book_appointment",
                "description": (
                    "Create a confirmed appointment after check_availability returned available=true. "
                    "Requires caller name and phone."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Caller full name"},
                        "phone": {
                            "type": "string",
                            "description": "Caller phone E.164 or US format",
                        },
                        "date": {
                            "type": "string",
                            "description": VAPI_TOOL_DATE_PARAM_HINT,
                        },
                        "time": {
                            "type": "string",
                            "description": VAPI_TOOL_TIME_PARAM_HINT,
                        },
                        "notes": {
                            "type": "string",
                            "description": "Optional appointment notes",
                        },
                    },
                    "required": ["name", "phone", "date", "time"],
                },
            },
            "async": False,
            "server": {
                "url": server_url,
                "method": "POST",
                "headers": {
                    "x-api-key": "USE_RENDER_ENV_VAPI_API_KEY",
                },
            },
        },
    ]


def vapi_setup_instructions() -> Dict[str, Any]:
    return {
        "server_url": f"{public_api_base_url()}/vapi/webhook",
        "server_url_method": "POST",
        "server_url_header": "x-api-key: <VAPI_API_KEY from Render>",
        "phone_number_config": {
            "assistantId": None,
            "squadId": None,
            "server": {"url": f"{public_api_base_url()}/vapi/webhook"},
            "note": "Leave assistantId unset on the phone number so VAPI sends assistant-request.",
        },
        "base_assistant_dashboard": {
            "env": "VAPI_BASE_ASSISTANT_ID",
            "system_prompt": "Minimal generic prompt only; backend overrides per call via assistant-request.",
            "optional_placeholders": [
                "{{business_name}}",
                "{{business_prompt}}",
                "{{timezone}}",
            ],
        },
        "tools": vapi_tool_definitions(),
        "do_not": [
            "Do not use GET for tools",
            "Do not hardcode clinic/business names in the static VAPI assistant prompt",
            "Do not set a fixed assistantId on the phone number if using dynamic assistant-request",
        ],
    }
