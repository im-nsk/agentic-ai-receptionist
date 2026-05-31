"""VAPI / Twilio webhook payload normalization and inbound-number extraction."""

from __future__ import annotations

import json
import os
import re
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from backend.models.client import Client
from backend.services.tenant_resolver import (
    TenantContext,
    normalize_inbound_phone,
    resolve_client_by_inbound_number,
)

# Max chars per log line (Render); payload logged in chunks.
_RAW_CHUNK = 8000

# Known JSON paths for the business / Twilio *destination* line (called number).
# Order matters: more specific VAPI/Twilio paths first.
_INBOUND_TO_PATHS: Tuple[Tuple[str, ...], ...] = (
    ("message", "phoneNumber", "twilioPhoneNumber"),
    ("message", "phoneNumber", "number"),
    ("message", "call", "phoneNumber", "twilioPhoneNumber"),
    ("message", "call", "phoneNumber", "number"),
    ("phoneNumber", "twilioPhoneNumber"),
    ("phoneNumber", "number"),
    ("call", "phoneNumber", "twilioPhoneNumber"),
    ("call", "phoneNumber", "number"),
    ("message", "call", "phoneNumberId"),  # resolved via DB below
    ("call", "phoneNumberId"),
    ("message", "phoneNumberId"),
    ("twilio", "to"),
    ("twilio", "To"),
    ("To",),
    ("to",),
    ("to_number",),
    ("toNumber",),
    ("business_phone",),
    ("twilio_number",),
)

# Keys that often hold E.164 when walking the tree.
_PHONE_VALUE_KEYS = frozenset(
    {
        "twilioPhoneNumber",
        "twilio_phone_number",
        "number",
        "phoneNumber",
        "to",
        "To",
        "to_number",
        "toNumber",
        "business_phone",
        "twilio_number",
    }
)

_TOOL_CALL_MARKERS = frozenset(
    {
        "toolCallList",
        "toolWithToolCallList",
        "toolCalls",
        "tool_calls",
    }
)

# Fields VAPI may POST at root when using a per-tool server URL (alongside call metadata).
_FLAT_TOOL_ARG_KEYS = frozenset(
    {
        "name",
        "customer_name",
        "date",
        "time",
        "phone",
        "customer_phone",
        "caller_phone",
        "notes",
        "note",
        "appointment_date",
        "appointment_time",
        "to_number",
        "toNumber",
    }
)

_VAPI_CALL_CONTEXT_KEYS = frozenset(
    {
        "call",
        "phoneNumber",
        "assistant",
        "customer",
        "assistantId",
        "phoneNumberId",
        "artifact",
        "type",
        "timestamp",
    }
)


def log_vapi_raw_payload(body: Any) -> None:
    """Log complete webhook JSON (structure preserved, secrets not redacted)."""
    try:
        raw = json.dumps(body, default=str, ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        raw = repr(body) + f" (json.dumps failed: {exc!r})"
    print(f"[VAPI RAW PAYLOAD] bytes={len(raw)}")
    if len(raw) <= _RAW_CHUNK:
        print(f"[VAPI RAW PAYLOAD JSON] {raw}")
        return
    for i, start in enumerate(range(0, len(raw), _RAW_CHUNK)):
        print(f"[VAPI RAW PAYLOAD JSON part={i + 1}] {raw[start : start + _RAW_CHUNK]}")


def _get_nested(obj: Any, path: Tuple[str, ...]) -> Any:
    cur = obj
    for key in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def _looks_like_phone(value: str) -> bool:
    if not value or "@" in value:
        return False
    digits = re.sub(r"\D", "", value)
    return len(digits) >= 10


def _coerce_phone_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)):
        return str(value).strip()
    if isinstance(value, dict):
        for key in (
            "twilioPhoneNumber",
            "twilio_phone_number",
            "number",
            "phoneNumber",
            "e164",
            "value",
        ):
            if key in value:
                found = _coerce_phone_value(value[key])
                if found:
                    return found
    return ""


def _walk_phone_candidates(
    obj: Any,
    *,
    path: str = "",
    out: Optional[List[Tuple[str, str]]] = None,
    depth: int = 0,
    max_depth: int = 12,
) -> List[Tuple[str, str]]:
    """Collect (json_path, phone_string) from nested objects."""
    if out is None:
        out = []
    if depth > max_depth or obj is None:
        return out

    if isinstance(obj, dict):
        for key, val in obj.items():
            child_path = f"{path}.{key}" if path else key
            if key in _PHONE_VALUE_KEYS:
                s = _coerce_phone_value(val)
                if _looks_like_phone(s):
                    out.append((child_path, s))
            _walk_phone_candidates(val, path=child_path, out=out, depth=depth + 1, max_depth=max_depth)
    elif isinstance(obj, list):
        for i, item in enumerate(obj[:20]):
            _walk_phone_candidates(
                item,
                path=f"{path}[{i}]",
                out=out,
                depth=depth + 1,
                max_depth=max_depth,
            )
    return out


def normalize_vapi_body(body: dict) -> Tuple[dict, dict]:
    """
    Return (envelope, message) where message is the VAPI server message object.

    Handles:
    - Standard: { "message": { "type": "tool-calls", ... } }
    - Root-level tool-calls (some proxies / older configs)
    """
    if not isinstance(body, dict):
        return body if isinstance(body, dict) else {}, {}

    msg = body.get("message")
    if isinstance(msg, dict):
        return body, msg

    if body.get("type") == "tool-calls" or any(k in body for k in _TOOL_CALL_MARKERS):
        return {"message": body}, body

    return body, msg if isinstance(msg, dict) else {}


def is_vapi_tool_calls_envelope(body: dict) -> bool:
    """True when this request is a VAPI tool-calls server message (not flat manual JSON)."""
    if not isinstance(body, dict):
        return False
    _, message = normalize_vapi_body(body)
    if message.get("type") == "tool-calls":
        return True
    if any(k in message for k in _TOOL_CALL_MARKERS):
        return True
    if any(k in body for k in _TOOL_CALL_MARKERS) and body.get("type") == "tool-calls":
        return True
    return False


def has_vapi_call_context_at_root(body: dict) -> bool:
    """VAPI call metadata present without a ``message`` wrapper (common on per-tool URLs)."""
    if not isinstance(body, dict):
        return False
    return any(k in body for k in _VAPI_CALL_CONTEXT_KEYS)


def split_root_flat_tool_body(body: dict) -> Tuple[dict, dict]:
    """
    Split per-tool URL body into (tool_arguments, pseudo_message_for_tenant_extraction).
    """
    tool_args = {k: body[k] for k in _FLAT_TOOL_ARG_KEYS if k in body}
    message = {k: v for k, v in body.items() if k not in _FLAT_TOOL_ARG_KEYS}
    return tool_args, message


def is_flat_tool_args_with_call_context(body: dict) -> bool:
    """
    VAPI per-tool server URL: booking fields + ``call`` / ``phoneNumber`` at root (no ``message``).
    """
    if not isinstance(body, dict) or is_vapi_tool_calls_envelope(body):
        return False
    if "message" in body and isinstance(body.get("message"), dict):
        return False
    has_booking = any(k in body for k in ("date", "time", "name", "phone", "customer_name"))
    return has_booking and has_vapi_call_context_at_root(body)


def is_manual_flat_test_payload(body: dict) -> bool:
    """
    Flat JSON for curl/manual tests — booking fields only, no VAPI call envelope.
    Tenant resolution uses TWILIO_PHONE / VAPI_DEFAULT_CLIENT_ID env fallbacks.
    """
    if not isinstance(body, dict):
        return False
    if is_vapi_tool_calls_envelope(body):
        return False
    if is_flat_tool_args_with_call_context(body):
        return False
    if "message" in body and isinstance(body.get("message"), dict):
        return False
    if any(k in body for k in _TOOL_CALL_MARKERS):
        return False
    if has_vapi_call_context_at_root(body):
        return False
    return any(k in body for k in ("date", "time", "name", "phone", "customer_name"))


def extract_vapi_assistant_id(body: dict, message: dict) -> str:
    for root in (message, body):
        if not isinstance(root, dict):
            continue
        call = root.get("call") if isinstance(root.get("call"), dict) else {}
        assistant = root.get("assistant") if isinstance(root.get("assistant"), dict) else {}
        for val in (
            root.get("assistantId"),
            call.get("assistantId"),
            assistant.get("id"),
        ):
            if val:
                return str(val).strip()
    return ""


def extract_vapi_phone_number_id(body: dict, message: dict) -> str:
    for root in (message, body):
        if not isinstance(root, dict):
            continue
        call = root.get("call") if isinstance(root.get("call"), dict) else {}
        pn = root.get("phoneNumber") if isinstance(root.get("phoneNumber"), dict) else {}
        for val in (
            call.get("phoneNumberId"),
            pn.get("id"),
            root.get("phoneNumberId"),
        ):
            if val and not _looks_like_phone(str(val)):
                return str(val).strip()
    return ""


def extract_inbound_to_candidates(
    body: dict,
    message: dict,
    tool_args: Optional[dict] = None,
) -> List[Tuple[str, str]]:
    """Ordered (source, raw_phone) candidates for tenant resolution."""
    tool_args = tool_args or {}
    seen: set[str] = set()
    ordered: List[Tuple[str, str]] = []

    def add(source: str, raw: str) -> None:
        raw = (raw or "").strip()
        if raw.lower() in ("restricted", "unknown", "anonymous"):
            return
        if not raw or not _looks_like_phone(raw):
            return
        key = f"{source}:{raw}"
        if key in seen:
            return
        seen.add(key)
        ordered.append((source, raw))

    for path in _INBOUND_TO_PATHS:
        val = _get_nested(body, path)
        if val is None and path[0] not in ("message", "call", "phoneNumber", "twilio"):
            val = _get_nested(tool_args, path)
        if val is None:
            continue
        if path[-1] == "phoneNumberId" or path[-1] == "phoneNumberId":
            continue  # IDs handled separately
        s = _coerce_phone_value(val)
        add("path:" + ".".join(path), s)

    for key in ("to_number", "toNumber", "business_phone", "twilio_number", "To", "to"):
        if key in tool_args:
            val = _coerce_phone_value(tool_args[key])
            if str(tool_args.get(key) or "").strip().lower() in ("restricted", ""):
                print(
                    "[VAPI TOOL ARGS]",
                    f"{key}={tool_args.get(key)!r} ignored for tenant lookup",
                )
            add(f"tool_args.{key}", val)

    for path, phone in _walk_phone_candidates(body):
        if "customer" in path.lower():
            continue
        add(f"walk:body.{path}", phone)
    for path, phone in _walk_phone_candidates(message):
        if "customer" in path.lower():
            continue
        add(f"walk:message.{path}", phone)

    return ordered


def extract_caller_from_candidates(
    body: dict,
    message: dict,
    tool_args: Optional[dict] = None,
) -> str:
    tool_args = tool_args or {}
    for key in ("phone", "customer_phone", "caller_phone", "from_number", "fromNumber"):
        if key in tool_args:
            s = _coerce_phone_value(tool_args[key])
            if _looks_like_phone(s):
                return s

    call = message.get("call") if isinstance(message.get("call"), dict) else {}
    customer = call.get("customer") if isinstance(call.get("customer"), dict) else {}
    if isinstance(message.get("customer"), dict):
        customer = message["customer"]
    for src in (
        customer.get("number"),
        customer,
        call.get("customerNumber"),
        _get_nested(body, "customer", "number"),
    ):
        s = _coerce_phone_value(src)
        if _looks_like_phone(s):
            return s
    return ""


def resolve_client_by_vapi_phone_number_id(
    db: Session,
    phone_number_id: str,
    *,
    log_prefix: str = "VAPI",
) -> Optional[TenantContext]:
    if not phone_number_id:
        return None
    client = (
        db.query(Client)
        .filter(Client.vapi_phone_number_id == phone_number_id)
        .first()
    )
    if not client:
        print(
            f"{log_prefix} phoneNumberId NO MATCH",
            f"vapi_phone_number_id={phone_number_id!r}",
        )
        return None
    ctx = TenantContext.from_client(
        client,
        inbound_number=(client.twilio_number or client.phone_number or "").strip(),
        match_field="vapi_phone_number_id",
    )
    print(f"{log_prefix} phoneNumberId MATCHED:", ctx.log_fields())
    return ctx


def resolve_client_by_vapi_assistant_id(
    db: Session,
    assistant_id: str,
    *,
    log_prefix: str = "VAPI",
) -> Optional[TenantContext]:
    if not assistant_id:
        return None
    client = db.query(Client).filter(Client.vapi_assistant_id == assistant_id).first()
    if not client:
        print(
            f"{log_prefix} assistantId NO MATCH",
            f"vapi_assistant_id={assistant_id!r}",
        )
        return None
    ctx = TenantContext.from_client(
        client,
        inbound_number=(client.twilio_number or client.phone_number or "").strip(),
        match_field="vapi_assistant_id",
    )
    print(f"{log_prefix} assistantId MATCHED:", ctx.log_fields())
    return ctx


def resolve_client_by_env_vapi_id_match(
    db: Session,
    body: dict,
    message: dict,
    *,
    log_prefix: str = "VAPI",
) -> Optional[TenantContext]:
    """
    Render env-only fallback: when payload IDs match VAPI_ASSISTANT_ID / VAPI_PHONE_NUMBER_ID,
    resolve via VAPI_DEFAULT_CLIENT_ID or single assigned twilio_number client.
    """
    env_asst = (os.getenv("VAPI_ASSISTANT_ID") or "").strip()
    env_pn = (os.getenv("VAPI_PHONE_NUMBER_ID") or "").strip()
    payload_asst = extract_vapi_assistant_id(body, message)
    payload_pn = extract_vapi_phone_number_id(body, message)

    matched = False
    if env_asst and payload_asst and env_asst == payload_asst:
        print(f"[VAPI FALLBACK]", "payload assistantId matches VAPI_ASSISTANT_ID env")
        matched = True
    if env_pn and payload_pn and env_pn == payload_pn:
        print(f"[VAPI FALLBACK]", "payload phoneNumberId matches VAPI_PHONE_NUMBER_ID env")
        matched = True

    # Single-tenant: env IDs set, payload omits IDs (flat tool POST)
    if not matched and (env_asst or env_pn):
        if not payload_asst and not payload_pn and os.getenv("VAPI_DEFAULT_CLIENT_ID"):
            print(
                f"[VAPI FALLBACK]",
                "VAPI_ASSISTANT_ID/VAPI_PHONE_NUMBER_ID env set, flat payload without IDs",
            )
            matched = True

    if not matched:
        return None

    return resolve_client_default_single_tenant(db, log_prefix=log_prefix)


def resolve_client_default_single_tenant(
    db: Session,
    *,
    log_prefix: str = "VAPI",
) -> Optional[TenantContext]:
    """VAPI_DEFAULT_CLIENT_ID or exactly one client with twilio_number assigned."""
    default_id = (os.getenv("VAPI_DEFAULT_CLIENT_ID") or "").strip()
    if default_id:
        try:
            cid = uuid.UUID(default_id)
        except ValueError:
            print(f"{log_prefix} invalid VAPI_DEFAULT_CLIENT_ID={default_id!r}")
            return None
        client = db.query(Client).filter(Client.id == cid).first()
        if client:
            ctx = TenantContext.from_client(
                client,
                inbound_number=(client.twilio_number or "").strip(),
                match_field="vapi_default_client_id",
            )
            print(f"{log_prefix} DEFAULT_CLIENT_ID MATCHED:", ctx.log_fields())
            return ctx
        print(f"{log_prefix} VAPI_DEFAULT_CLIENT_ID not found: {default_id!r}")
        return None

    assigned = (
        db.query(Client)
        .filter(Client.twilio_number.isnot(None), Client.twilio_number != "")
        .all()
    )
    if len(assigned) == 1:
        client = assigned[0]
        ctx = TenantContext.from_client(
            client,
            inbound_number=client.twilio_number or "",
            match_field="single_tenant_auto",
        )
        print(f"{log_prefix} SINGLE TENANT AUTO MATCHED:", ctx.log_fields())
        return ctx
    return None


@dataclass
class VapiTenantResolution:
    tenant: Optional[TenantContext]
    extracted_to: str
    resolution_method: str
    all_candidates: List[Tuple[str, str]]


def resolve_tenant_from_vapi_payload(
    db: Session,
    body: dict,
    message: dict,
    tool_args: Optional[dict] = None,
    *,
    log_prefix: str = "VAPI",
) -> VapiTenantResolution:
    """
    Resolve tenant using inbound Twilio number, then fallbacks (never silent empty To).
    """
    tool_args = tool_args or {}
    candidates = extract_inbound_to_candidates(body, message, tool_args)
    print(
        f"[VAPI EXTRACTED TO NUMBER]",
        f"candidates={candidates!r}",
    )

    env_twilio = (os.getenv("TWILIO_PHONE") or "").strip()
    if env_twilio:
        candidates.append(("env:TWILIO_PHONE", env_twilio))

    tenant: Optional[TenantContext] = None
    extracted_to = ""
    method = ""

    for source, raw in candidates:
        normalized = normalize_inbound_phone(raw)
        if not normalized:
            continue
        tenant = resolve_client_by_inbound_number(db, raw, log_prefix=log_prefix)
        if tenant:
            extracted_to = normalized
            method = source
            break

    if not tenant:
        pn_id = extract_vapi_phone_number_id(body, message)
        if pn_id:
            print(f"[VAPI FALLBACK]", f"trying phoneNumberId={pn_id!r}")
            tenant = resolve_client_by_vapi_phone_number_id(db, pn_id, log_prefix=log_prefix)
            if tenant:
                method = f"phoneNumberId:{pn_id}"
                extracted_to = tenant.inbound_number

    if not tenant:
        asst_id = extract_vapi_assistant_id(body, message)
        if asst_id:
            print(f"[VAPI FALLBACK]", f"trying assistantId={asst_id!r}")
            tenant = resolve_client_by_vapi_assistant_id(db, asst_id, log_prefix=log_prefix)
            if tenant:
                method = f"assistantId:{asst_id}"
                extracted_to = tenant.inbound_number

    if not tenant:
        tenant = resolve_client_by_env_vapi_id_match(
            db, body, message, log_prefix=log_prefix
        )
        if tenant:
            method = tenant.match_field
            extracted_to = tenant.inbound_number

    if not tenant:
        print("[VAPI FALLBACK]", "trying VAPI_DEFAULT_CLIENT_ID / single assigned tenant")
        tenant = resolve_client_default_single_tenant(db, log_prefix=log_prefix)
        if tenant:
            method = tenant.match_field
            extracted_to = tenant.inbound_number

    if not tenant:
        print(
            "[VAPI TENANT RESOLUTION FAILED]",
            "no client matched; booking will not run",
            f"TWILIO_PHONE env set={bool(os.getenv('TWILIO_PHONE'))}",
            f"VAPI_DEFAULT_CLIENT_ID set={bool(os.getenv('VAPI_DEFAULT_CLIENT_ID'))}",
        )

    if tenant:
        print(
            "[VAPI CLIENT RESOLVED]",
            f"method={method!r}",
            f"extracted_to={extracted_to!r}",
            tenant.log_fields(),
        )
    else:
        print(
            "[VAPI CLIENT RESOLVED]",
            "FAILED",
            f"assistantId={extract_vapi_assistant_id(body, message)!r}",
            f"phoneNumberId={extract_vapi_phone_number_id(body, message)!r}",
            "hint=set clients.twilio_number via /admin/twilio/assign, "
            "or clients.vapi_assistant_id / vapi_phone_number_id, or VAPI_DEFAULT_CLIENT_ID",
        )

    return VapiTenantResolution(
        tenant=tenant,
        extracted_to=extracted_to,
        resolution_method=method,
        all_candidates=candidates,
    )
