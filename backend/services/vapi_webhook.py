"""VAPI server URL protocol: tool-calls, transcripts, and routing to voice booking."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple

from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from backend.services.vapi_payload import (
    extract_caller_from_candidates,
    is_flat_tool_args_with_call_context,
    is_manual_flat_test_payload,
    is_vapi_tool_calls_envelope,
    log_vapi_raw_payload,
    normalize_vapi_body,
    resolve_tenant_from_vapi_payload,
    split_root_flat_tool_body,
)
from backend.services.voice_booking import (
    execute_voice_book,
    execute_voice_check_availability,
)

# Tool names configured in VAPI dashboard (aliases supported).
# VAPI tool param descriptions: voice_datetime.VAPI_TOOL_DATE_PARAM_HINT / TIME.
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


def log_vapi_incoming(body: dict) -> None:
    log_vapi_raw_payload(body)
    _body, message = normalize_vapi_body(body)
    msg_type = message.get("type") or (
        "legacy-flat" if is_manual_flat_test_payload(body) else "unknown"
    )
    call = message.get("call") if isinstance(message.get("call"), dict) else {}
    call_id = str(call.get("id") or "")
    print(
        "[VAPI WEBHOOK INCOMING]",
        f"message_type={msg_type!r}",
        f"call_id={call_id!r}",
        f"top_level_keys={list(body.keys()) if isinstance(body, dict) else []!r}",
    )
    _log_transcript_snippet(message)
    if msg_type == "tool-calls" or is_vapi_tool_calls_envelope(body):
        for tc in _iter_tool_calls(message):
            print(
                "[VAPI TOOL CALL DETECTED]",
                f"tool={tc.get('name')!r}",
                f"toolCallId={tc.get('id')!r}",
                f"arguments={json.dumps(_tool_args(tc), default=str)!r}",
            )


def _log_transcript_snippet(message: dict) -> None:
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
    raw = message.get("toolCallList") or message.get("toolCalls")
    if isinstance(raw, list):
        out.extend([x for x in raw if isinstance(x, dict)])
    twtcl = message.get("toolWithToolCallList")
    if isinstance(twtcl, list):
        for entry in twtcl:
            if not isinstance(entry, dict):
                continue
            tc = entry.get("toolCall")
            if isinstance(tc, dict):
                built = {
                    "id": tc.get("id"),
                    "name": entry.get("name") or (tc.get("function") or {}).get("name"),
                    "arguments": (tc.get("function") or {}).get("parameters")
                    or tc.get("parameters")
                    or {},
                }
                if built not in out:
                    out.append(built)
    return out


def _tool_args(tool_call: dict) -> dict:
    raw = tool_call.get("arguments") or tool_call.get("parameters") or {}
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return {}
    return raw if isinstance(raw, dict) else {}


def _detect_intent(tool_name: str) -> str:
    norm = _normalize_tool_name(tool_name)
    if norm in {_normalize_tool_name(t) for t in BOOK_APPOINTMENT_TOOLS}:
        return "book_appointment"
    if norm in {_normalize_tool_name(t) for t in CHECK_AVAILABILITY_TOOLS}:
        return "check_availability"
    return f"unknown:{tool_name}"


def _tenant_resolution_error(resolution: Any, tool_name: str) -> str:
    if resolution.all_candidates:
        return (
            "Could not resolve business from call payload. "
            f"Tried phone candidates={resolution.all_candidates!r}. "
            "Assign clients.twilio_number or set vapi_assistant_id / VAPI_DEFAULT_CLIENT_ID."
        )
    return (
        "No inbound business phone number in VAPI payload. "
        "Assign twilio_number via /admin/twilio/assign or configure VAPI assistant/phone IDs."
    )


def _run_tool(
    db: Session,
    tenant: Any,
    tool_call: dict,
    background_tasks: BackgroundTasks,
    message: dict,
    body: dict,
) -> Tuple[str, str]:
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
        "[VAPI BOOKING TOOL START]",
        f"intent={intent!r}",
        f"tool={tool_name!r}",
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
        caller = extract_caller_from_candidates(body, message, args)
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
    _body, message = normalize_vapi_body(body)
    if not message:
        print("[VAPI WEBHOOK]", "tool-calls envelope missing message object")
        return {"results": []}

    results: List[dict] = []
    for tool_call in _iter_tool_calls(message):
        tool_id = str(tool_call.get("id") or "")
        tool_name = str(tool_call.get("name") or "")
        args = _tool_args(tool_call)

        resolution = resolve_tenant_from_vapi_payload(
            db, body, message, args, log_prefix="VAPI"
        )
        tenant = resolution.tenant
        if not tenant:
            err = _tenant_resolution_error(resolution, tool_name)
            print("[VOICE BOOKING FAILED]", f"reason={err}", f"tool={tool_name!r}")
            results.append({"toolCallId": tool_id, "error": err})
            continue

        try:
            tid, payload = _run_tool(
                db, tenant, tool_call, background_tasks, message, body
            )
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


def handle_flat_tool_with_call_context(
    body: dict,
    db: Session,
    background_tasks: BackgroundTasks,
) -> dict:
    """
    Per-tool VAPI URL: ``{ name, date, time, phone, call, phoneNumber, ... }`` at root.
    """
    tool_args, pseudo_message = split_root_flat_tool_body(body)
    resolution = resolve_tenant_from_vapi_payload(
        db, body, pseudo_message, tool_args, log_prefix="VAPI_FLAT_CTX"
    )
    tenant = resolution.tenant
    if not tenant:
        err = _tenant_resolution_error(resolution, "flat+context")
        print("[VOICE BOOKING FAILED]", f"reason={err}")
        return {"status": "failed", "message": err}

    is_book = bool(tool_args.get("name") or tool_args.get("customer_name"))
    print(
        "[VAPI ROUTE]",
        "protocol=flat-tool-args+call-context",
        f"resolution={resolution.resolution_method!r}",
        f"pseudo_message_keys={list(pseudo_message.keys())!r}",
        tenant.log_fields(),
    )

    if is_book:
        caller = extract_caller_from_candidates(body, pseudo_message, tool_args)
        return execute_voice_book(
            db,
            tenant,
            tool_args,
            background_tasks,
            tool_name="flat_tool_with_context",
            call_id=str((pseudo_message.get("call") or {}).get("id") or "flat-ctx"),
            default_caller_phone=caller,
        )

    return execute_voice_check_availability(
        db,
        tenant,
        tool_args,
        tool_name="flat_check_with_context",
        call_id=str((pseudo_message.get("call") or {}).get("id") or "flat-ctx"),
    )


def handle_manual_flat_request(
    body: dict,
    db: Session,
    background_tasks: BackgroundTasks,
    *,
    force_book: bool,
) -> dict:
    """
    Flat JSON (curl tests or VAPI per-tool URL posting only tool arguments).
    Uses full-body tenant extraction — not only body['to_number'].
    """
    _body, message = normalize_vapi_body(body)
    resolution = resolve_tenant_from_vapi_payload(
        db, body, message, body, log_prefix="VAPI_FLAT"
    )
    tenant = resolution.tenant
    if not tenant:
        err = _tenant_resolution_error(resolution, "flat")
        print("[VOICE BOOKING FAILED]", f"reason={err}")
        if force_book:
            return {"status": "failed", "message": err}
        return {"available": False, "message": err}

    is_book = force_book or bool(body.get("name") or body.get("customer_name"))
    print(
        "[VAPI ROUTE]",
        f"protocol=manual-flat-{'book' if is_book else 'check'}",
        f"resolution={resolution.resolution_method!r}",
        tenant.log_fields(),
    )

    if is_book:
        caller = extract_caller_from_candidates(body, message, body)
        return execute_voice_book(
            db,
            tenant,
            body,
            background_tasks,
            tool_name="manual_flat_book",
            call_id="flat",
            default_caller_phone=caller,
        )

    return execute_voice_check_availability(
        db,
        tenant,
        body,
        tool_name="manual_flat_check",
        call_id="flat",
    )


def dispatch_vapi_request(
    body: dict,
    db: Session,
    background_tasks: BackgroundTasks,
) -> dict:
    log_vapi_incoming(body)

    if is_vapi_tool_calls_envelope(body):
        print("[VAPI ROUTE]", "protocol=tool-calls (VAPI server URL envelope)")
        return handle_vapi_tool_calls(body, db, background_tasks)

    if is_flat_tool_args_with_call_context(body):
        return handle_flat_tool_with_call_context(body, db, background_tasks)

    if is_manual_flat_test_payload(body):
        force_book = bool(body.get("name") or body.get("customer_name"))
        return handle_manual_flat_request(
            body, db, background_tasks, force_book=force_book
        )

    _body, message = normalize_vapi_body(body)
    msg_type = message.get("type", "unknown") if message else "unknown"
    print(
        "[VAPI WEBHOOK ACK]",
        f"message_type={msg_type!r}",
        "(informational event — no tool execution)",
    )
    return {}
