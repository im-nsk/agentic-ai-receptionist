"""VAPI server URL protocol: tool-calls, transcripts, and routing to voice booking."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Tuple

from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from backend.services.tenant_resolver import TenantContext, resolve_client_by_inbound_number
from backend.services.voice_booking import (
    execute_voice_book,
    execute_voice_check_availability,
)

# Tool names configured in VAPI dashboard (aliases supported).
CHECK_AVAILABILITY_TOOLS = frozenset(
    {
        "check_availability",
        "checkavailability",
        "check-availability",
        "check_availability_slot",
        "availability",
    }
)
BOOK_APPOINTMENT_TOOLS = frozenset(
    {
        "book",
        "book_appointment",
        "bookappointment",
        "book-appointment",
        "create_booking",
        "schedule_appointment",
        "confirm_booking",
    }
)


def _normalize_tool_name(name: str) -> str:
    return (name or "").strip().lower().replace(" ", "_")


def is_vapi_tool_calls_payload(body: dict) -> bool:
    msg = body.get("message")
    return isinstance(msg, dict) and msg.get("type") == "tool-calls"


def is_legacy_flat_booking_payload(body: dict) -> bool:
    """Direct POST /vapi/book style (flat JSON) for manual testing."""
    if "message" in body:
        return False
    return any(k in body for k in ("to_number", "date", "time", "name", "phone"))


def log_vapi_incoming(body: dict) -> None:
    msg = body.get("message") if isinstance(body.get("message"), dict) else {}
    msg_type = msg.get("type") or ("legacy-flat" if is_legacy_flat_booking_payload(body) else "unknown")
    call = msg.get("call") if isinstance(msg.get("call"), dict) else {}
    call_id = str(call.get("id") or "")
    print(
        "[VAPI WEBHOOK INCOMING]",
        f"message_type={msg_type!r}",
        f"call_id={call_id!r}",
    )
    _log_transcript_snippet(msg)
    if msg_type == "tool-calls":
        for tc in _iter_tool_calls(msg):
            print(
                "[VAPI TOOL CALL DETECTED]",
                f"tool={tc.get('name')!r}",
                f"toolCallId={tc.get('id')!r}",
                f"arguments={json.dumps(_tool_args(tc), default=str)!r}",
            )


def _log_transcript_snippet(message: dict) -> None:
    """Log recent user/assistant lines from artifact (STT / model output)."""
    artifact = message.get("artifact")
    if not isinstance(artifact, dict):
        return
    messages = artifact.get("messages")
    if not isinstance(messages, list):
        return
    for item in messages[-6:]:
        if not isinstance(item, dict):
            continue
        role = item.get("role") or item.get("type")
        text = (
            item.get("message")
            or item.get("content")
            or item.get("text")
            or item.get("transcript")
            or ""
        )
        if isinstance(text, list):
            text = " ".join(str(x) for x in text)
        text = str(text).strip()
        if not text:
            continue
        if role in ("assistant", "bot", "model"):
            print(f"[VAPI AI RESPONSE] text={text[:500]!r}")
        else:
            print(f"[VAPI STT TRANSCRIPT] role={role!r} text={text[:500]!r}")


def _iter_tool_calls(message: dict) -> List[dict]:
    out: List[dict] = []
    raw = message.get("toolCallList")
    if isinstance(raw, list):
        out.extend([x for x in raw if isinstance(x, dict)])
    twtcl = message.get("toolWithToolCallList")
    if isinstance(twtcl, list):
        for entry in twtcl:
            if not isinstance(entry, dict):
                continue
            tc = entry.get("toolCall")
            if isinstance(tc, dict) and tc not in out:
                out.append(
                    {
                        "id": tc.get("id"),
                        "name": entry.get("name") or (tc.get("function") or {}).get("name"),
                        "arguments": (tc.get("function") or {}).get("parameters")
                        or tc.get("parameters")
                        or {},
                    }
                )
    return out


def _tool_args(tool_call: dict) -> dict:
    raw = tool_call.get("arguments") or tool_call.get("parameters") or {}
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return {}
    return raw if isinstance(raw, dict) else {}


def _extract_phone_from_call_obj(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        return str(value.get("number") or value.get("phoneNumber") or "").strip()
    return ""


def extract_inbound_to_number(message: dict, tool_args: dict) -> str:
    """
    Twilio/VAPI business line (maps to clients.twilio_number).
    """
    for key in ("to_number", "toNumber", "business_phone", "twilio_number"):
        v = tool_args.get(key)
        if v:
            return str(v).strip()

    # VAPI ServerMessageToolCalls.phoneNumber (assistant's inbound line)
    pn = message.get("phoneNumber")
    num = _extract_phone_from_call_obj(pn)
    if num and "@" not in num:
        return num

    call = message.get("call") if isinstance(message.get("call"), dict) else {}
    for path in (
        call.get("phoneNumber"),
        call.get("phoneNumberId"),  # sometimes only id — fallback below
        message.get("phoneNumber"),
    ):
        num = _extract_phone_from_call_obj(path)
        if num and "@" not in num:
            return num

    env_fallback = (os.getenv("TWILIO_PHONE") or "").strip()
    return env_fallback


def extract_caller_phone(message: dict, tool_args: dict) -> str:
    for key in ("phone", "customer_phone", "caller_phone", "from_number", "fromNumber"):
        v = tool_args.get(key)
        if v:
            return str(v).strip()

    call = message.get("call") if isinstance(message.get("call"), dict) else {}
    customer = call.get("customer") if isinstance(call.get("customer"), dict) else {}
    return _extract_phone_from_call_obj(customer.get("number") or customer)


def resolve_tenant_for_vapi_call(
    db: Session,
    message: dict,
    tool_args: dict,
) -> Optional[TenantContext]:
    to_number = extract_inbound_to_number(message, tool_args)
    tenant = resolve_client_by_inbound_number(db, to_number, log_prefix="VAPI")
    if not tenant:
        print(
            "[VAPI TENANT MISS]",
            f"to_number={to_number!r}",
            "hint=assign TWILIO_PHONE to client via /admin/twilio/assign",
        )
    return tenant


def _detect_intent(tool_name: str) -> str:
    norm = _normalize_tool_name(tool_name)
    if norm in {_normalize_tool_name(t) for t in BOOK_APPOINTMENT_TOOLS}:
        return "book_appointment"
    if norm in {_normalize_tool_name(t) for t in CHECK_AVAILABILITY_TOOLS}:
        return "check_availability"
    return f"unknown:{tool_name}"


def _run_tool(
    db: Session,
    tenant: TenantContext,
    tool_call: dict,
    background_tasks: BackgroundTasks,
    message: dict,
) -> Tuple[str, Optional[str]]:
    """Returns (toolCallId, result_json_string). error string if failed."""
    tool_id = str(tool_call.get("id") or "")
    tool_name = str(tool_call.get("name") or "")
    args = _tool_args(tool_call)
    intent = _detect_intent(tool_name)
    call = message.get("call") if isinstance(message.get("call"), dict) else {}
    call_id = str(call.get("id") or "")

    print(
        "[VAPI INTENT DETECTED]",
        f"intent={intent!r}",
        f"tool={tool_name!r}",
        f"call_id={call_id!r}",
    )
    print(
        "[VAPI BOOKING TRIGGER]",
        f"intent={intent!r}",
        f"tool={tool_name!r}",
        f"call_id={call_id!r}",
        tenant.log_fields(),
    )

    if intent == "check_availability":
        result = execute_voice_check_availability(
            db,
            tenant,
            args,
            tool_name=tool_name,
            call_id=call_id,
        )
        return tool_id, json.dumps(result, default=str)

    if intent == "book_appointment":
        caller = extract_caller_phone(message, args)
        result = execute_voice_book(
            db,
            tenant,
            args,
            background_tasks,
            tool_name=tool_name,
            call_id=call_id,
            default_caller_phone=caller,
        )
        return tool_id, json.dumps(result, default=str)

    err = f"Unknown tool: {tool_name}"
    print("[VAPI TOOL SKIP]", err)
    return tool_id, json.dumps({"error": err})


def handle_vapi_tool_calls(
    body: dict,
    db: Session,
    background_tasks: BackgroundTasks,
) -> dict:
    """
    VAPI-required response shape (HTTP 200):
    { "results": [ { "toolCallId": "...", "result": "<json string>" } ] }
    """
    message = body.get("message") or {}
    if not isinstance(message, dict):
        return {"results": []}

    results: List[dict] = []
    for tool_call in _iter_tool_calls(message):
        tool_id = str(tool_call.get("id") or "")
        tool_name = str(tool_call.get("name") or "")
        args = _tool_args(tool_call)

        tenant = resolve_tenant_for_vapi_call(db, message, args)
        if not tenant:
            err = "No business found for this phone number. Check twilio_number assignment."
            print("[VOICE BOOKING FAILED]", f"reason={err}", f"tool={tool_name!r}")
            results.append(
                {
                    "toolCallId": tool_id,
                    "error": err,
                }
            )
            continue

        try:
            tid, payload = _run_tool(db, tenant, tool_call, background_tasks, message)
            if not tid:
                tid = tool_id
            results.append({"toolCallId": tid, "result": payload})
            print(
                "[VAPI TOOL RESPONSE]",
                f"toolCallId={tid!r}",
                f"result_preview={payload[:300]!r}",
            )
        except Exception as exc:
            err = f"Tool execution failed: {exc!r}"
            print("[VOICE BOOKING FAILED]", f"tool={tool_name!r}", f"reason={err!r}")
            results.append({"toolCallId": tool_id, "error": err})

    if not results:
        print("[VAPI WEBHOOK]", "tool-calls message had no toolCallList entries")

    return {"results": results}


def handle_legacy_flat_check(
    body: dict,
    db: Session,
) -> dict:
    """Backward-compatible flat JSON for /vapi/check-availability."""
    to_number = str(body.get("to_number") or "").strip()
    tenant = resolve_client_by_inbound_number(db, to_number, log_prefix="VAPI_LEGACY")
    if not tenant:
        return {"available": False, "message": "Client not found for this phone number"}

    print("[VAPI LEGACY FLAT CHECK]", tenant.log_fields())
    return execute_voice_check_availability(
        db,
        tenant,
        body,
        tool_name="legacy_flat_check",
        call_id="legacy",
    )


def handle_legacy_flat_book(
    body: dict,
    db: Session,
    background_tasks: BackgroundTasks,
) -> dict:
    """Backward-compatible flat JSON POST (manual / old VAPI custom URL per tool)."""
    to_number = str(body.get("to_number") or "").strip()
    tenant = resolve_client_by_inbound_number(db, to_number, log_prefix="VAPI_LEGACY")
    if not tenant:
        return {"status": "failed", "message": "Client not found for this phone number"}

    print("[VAPI LEGACY FLAT BOOK]", tenant.log_fields(), f"body_keys={list(body.keys())}")
    return execute_voice_book(
        db,
        tenant,
        body,
        background_tasks,
        tool_name="legacy_flat_book",
        call_id="legacy",
        default_caller_phone=str(body.get("phone") or ""),
    )


def dispatch_vapi_request(
    body: dict,
    db: Session,
    background_tasks: BackgroundTasks,
) -> dict:
    """
    Single entry for VAPI server URL and legacy tool URLs.
    """
    log_vapi_incoming(body)

    if is_vapi_tool_calls_payload(body):
        print("[VAPI ROUTE]", "protocol=tool-calls (VAPI server URL)")
        return handle_vapi_tool_calls(body, db, background_tasks)

    if is_legacy_flat_booking_payload(body):
        if body.get("name") or body.get("customer_name"):
            print("[VAPI ROUTE]", "protocol=legacy-flat-book")
            return handle_legacy_flat_book(body, db, background_tasks)
        print("[VAPI ROUTE]", "protocol=legacy-flat-check")
        return handle_legacy_flat_check(body, db)

    msg = body.get("message") if isinstance(body.get("message"), dict) else {}
    msg_type = msg.get("type", "unknown")
    print(
        "[VAPI WEBHOOK ACK]",
        f"message_type={msg_type!r}",
        "(informational event — no tool execution)",
    )
    return {}
