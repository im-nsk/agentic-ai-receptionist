# VAPI multi-tenant voice architecture

## What was wrong

1. **Static VAPI assistant** — Dashboard prompt said "clinic receptionist" for every caller. `clients.free_text` (`business_prompt`) was never injected at call time.
2. **`assistant-request` never fired** — If the VAPI **phone number** still has a fixed `assistantId`, VAPI uses the published assistant for the whole call and only POSTs `tool-calls` to your server. Tenant resolution on tool-calls does **not** change the voice prompt.
3. **Partial overrides** — `assistantId` + `assistantOverrides.model.messages` alone can merge with the published assistant; the dashboard system line may still win. Default is now **inline full `assistant`** (`VAPI_USE_INLINE_ASSISTANT=true`).
3. **Availability UX** — Tool returned `available: false` without `alternative_slots` or `voice_instruction`, so the LLM treated it as a system failure.
4. **Tool HTTP method** — Tools configured as GET while backend expects POST JSON (`tool-calls` envelope).
5. **`to_number` in tool args** — Optional; tenant is resolved server-side from the call payload (Twilio/VAPI phone metadata).

## Target architecture

```
Inbound call → Twilio → VAPI
    │
    ├─ (1) assistant-request  POST /vapi/webhook
    │       → resolve tenant (twilio_number / phoneNumberId / assistantId)
    │       → load business_name, business_prompt, services, timezone from DB
    │       → return assistantId + assistantOverrides (system prompt, firstMessage)
    │
    └─ (2) tool-calls         POST /vapi/webhook (same URL)
            → check_availability → enrich with alternatives + voice_instruction
            → book_appointment   → same book_appointment_logic as web
```

## VAPI dashboard setup (one shared base assistant)

1. Create **one** generic assistant in VAPI (minimal system text — no "clinic"; optional `{{business_name}}` placeholders).
2. Set Render env: `VAPI_USE_INLINE_ASSISTANT=true` (default), `VAPI_VOICE_ID`, `VAPI_MODEL_*`.
3. On the **phone number** (critical):
   - `assistantId`: **null** / unset — forces `assistant-request` to your server before each call
   - `server.url`: `https://<api>/vapi/webhook`
   - Custom header: `x-api-key` = `VAPI_API_KEY`
4. Attach tools from `GET /vapi/tools/schema` — **POST** to the same server URL (not GET per tool URL).

### Verify in Render logs (per call)

| Log | Meaning |
|-----|---------|
| `[VAPI ASSISTANT REQUEST RECEIVED]` | Dynamic pipeline ran — good |
| `[VAPI SYSTEM PROMPT PREVIEW]` | Contains Wrixio + business_prompt |
| `[VAPI ASSISTANT RESPONSE OUT]` | JSON sent back to VAPI |
| Only `[VAPI ROUTE] protocol=tool-calls` | **Broken** — phone still bound to static assistant |

## Per-tenant data (DB)

| Field | Use |
|--------|-----|
| `twilio_number` | Primary inbound routing |
| `free_text` | `business_prompt` in system message |
| `business_name` | Greeting + context |
| `services` | Listed in system prompt |
| `timezone` | Booking + availability |
| `vapi_assistant_id` / `vapi_phone_number_id` | Fallback routing |

## Scaling to many numbers / businesses

- Assign each Twilio number → one `clients` row (`POST /admin/twilio/assign`).
- Same `VAPI_BASE_ASSISTANT_ID` for all calls; **per-call** overrides via `assistant-request`.
- No need to clone VAPI assistants per business.

## Tool response format (critical)

VAPI server URL **only** uses this HTTP 200 body:

```json
{ "results": [{ "toolCallId": "<id>", "result": "<single-line string>" }] }
```

- **`result`** must be a **string** (not a JSON object). The LLM reads this text directly.
- **`voice_instruction`**, **`assistant_should_say`**, etc. are **not** VAPI magic fields — they only work if converted into the `result` string.
- Use **`result`**, not `content`, `toolResult`, or `output` (those are not the server URL contract).
- **`error`** key is optional for true failures; scheduling rejections should still use **`result`** with conversational text so the assistant does not say "technical error".

Backend now sets `result` to natural language, e.g.:

`SCHEDULING (not a system error): I'm sorry, Wrixio aren't open on Sundays. Would Monday 2026-05-25 at 9:00 AM work?`

## to_number in tool args

The LLM often sends `to_number=""` or `to_number="Restricted"` (Twilio privacy). **Ignore it.** Tenant is resolved from `message.phoneNumber` / call metadata on the server URL request, not from tool arguments.

| Tag | When |
|-----|------|
| `[VAPI SESSION CONFIG]` | assistant-request resolved tenant |
| `[VAPI ASSISTANT OVERRIDE]` | Dynamic prompt / first message built |
| `[VAPI BUSINESS PROMPT]` | Tenant prompt loaded from DB |
| `[VAPI SLOT UNAVAILABLE]` | Slot taken / rules reject |
| `[VAPI TOOL RESPONSE]` | Tool result sent to VAPI |

## Env vars (Render only)

- `VAPI_API_KEY` — webhook auth header
- `VAPI_BASE_ASSISTANT_ID` — shared dashboard assistant
- `VAPI_MODEL_PROVIDER` / `VAPI_MODEL_NAME` — inline assistant fallback if base ID unset
- `VAPI_VOICE_PROVIDER` / `VAPI_VOICE_ID` — inline voice fallback
- `PUBLIC_API_URL` or `RENDER_EXTERNAL_URL` — schema/docs URLs

No secrets or business prompts in code.
