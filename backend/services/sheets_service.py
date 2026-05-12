"""Google Sheets booking log — provisioned workbooks, header self-heal, append rows."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import gspread
from google.oauth2 import service_account

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

BOOKING_HEADERS: List[str] = [
    "booking_id",
    "name",
    "phone",
    "date",
    "time",
    "status",
    "source",
    "notes",
    "created_at",
]

_N_COL = len(BOOKING_HEADERS)

_credentials_info = json.loads(os.getenv("GOOGLE_CREDENTIALS_JSON", "{}") or "{}")
_credentials = service_account.Credentials.from_service_account_info(_credentials_info, scopes=SCOPES)
_client = gspread.authorize(_credentials)


def _header_range_a1() -> str:
    if _N_COL < 1 or _N_COL > 26:
        raise ValueError("BOOKING_HEADERS must have 1–26 columns for range helper")
    end = chr(ord("A") + _N_COL - 1)
    return f"A1:{end}1"


def get_sheet(sheet_id: str):
    if not sheet_id:
        raise ValueError("Sheet ID missing")
    try:
        return _client.open_by_key(sheet_id).sheet1
    except Exception as e:
        print("❌ INIT SHEET ERROR:", repr(e))
        raise e


def _row1_matches_header(row: List[str]) -> bool:
    if not row:
        return False
    trimmed = [str(c).strip() for c in row[:_N_COL]]
    if len(trimmed) < _N_COL:
        return False
    return trimmed == BOOKING_HEADERS


def ensure_booking_sheet_headers(sheet_id: str) -> None:
    """Ensure row 1 matches required headers (self-heal). Safe to call before every write/read."""
    if not sheet_id:
        return
    try:
        ws = get_sheet(sheet_id)
        row1 = ws.row_values(1)
        if _row1_matches_header(row1):
            return
        rng = _header_range_a1()
        ws.update(rng, [BOOKING_HEADERS], value_input_option="RAW")
        print("✅ Repaired booking sheet header row")
    except Exception as e:
        print("❌ ensure_booking_sheet_headers:", repr(e))
        raise


def _apply_frozen_header_row(worksheet: gspread.Worksheet) -> None:
    """Freeze row 1; header warning-only protection (edits allowed with prompt)."""
    try:
        spreadsheet = worksheet.spreadsheet
        body = {
            "requests": [
                {
                    "updateSheetProperties": {
                        "properties": {
                            "sheetId": worksheet.id,
                            "gridProperties": {"frozenRowCount": 1},
                        },
                        "fields": "gridProperties.frozenRowCount",
                    }
                },
                {
                    "addProtectedRange": {
                        "protectedRange": {
                            "range": {
                                "sheetId": worksheet.id,
                                "startRowIndex": 0,
                                "endRowIndex": 1,
                                "startColumnIndex": 0,
                                "endColumnIndex": _N_COL,
                            },
                            "description": "Booking header row",
                            "warningOnly": True,
                        }
                    }
                },
            ]
        }
        spreadsheet.batch_update(body)
    except Exception as e:
        err = str(e).lower()
        if "already exists" in err or "duplicate" in err or "protectedrange" in err:
            return
        print("⚠️ Header format (freeze/protect) skipped:", repr(e))


def create_provisioned_booking_sheet(title: str) -> str:
    """
    Create a new spreadsheet owned by the service account, write headers, freeze + soft-protect row 1.
    Returns spreadsheet ID (for clients.sheet_id).

    Workbook title is fixed for a consistent tenant experience; ``title`` is kept for API compatibility.
    """
    _ = title  # unused; provisioning uses a single branded workbook name
    spreadsheet = _client.create("AI Receptionist Booking Sheet")
    ws = spreadsheet.sheet1
    rng = _header_range_a1()
    ws.update(rng, [BOOKING_HEADERS], value_input_option="RAW")
    _apply_frozen_header_row(ws)
    sid = spreadsheet.id
    print("✅ Provisioned booking sheet:", sid)
    return str(sid)


def save_to_sheet(
    *,
    booking_id: str,
    name: str,
    phone: str,
    date: str,
    time: str,
    sheet_id: str,
    status: str = "confirmed",
    source: str = "web",
    notes: str = "",
    created_at: Optional[str] = None,
) -> None:
    if not sheet_id:
        print("⚠️ Skipping sheet save (no sheet_id)")
        return
    ensure_booking_sheet_headers(sheet_id)
    ts = created_at or datetime.utcnow().isoformat() + "Z"
    row = [booking_id, name, phone, date, time, status, source, notes or "", ts]
    try:
        sheet = get_sheet(sheet_id)
        sheet.append_row(row, value_input_option="RAW")
        print("✅ Saved booking row to Google Sheet")
    except Exception as e:
        print("❌ Sheet Error:", repr(e))
        raise


def list_booking_rows_for_dashboard(sheet_id: str, limit: int = 500) -> List[Dict[str, Any]]:
    """Read booking rows from the sheet (newest first by row order, trimmed to limit)."""
    if not sheet_id:
        return []
    ensure_booking_sheet_headers(sheet_id)
    ws = get_sheet(sheet_id)
    rows = ws.get_all_values()
    if len(rows) < 2:
        return []
    header = [str(c).strip() for c in rows[0][: _N_COL]]
    if header != BOOKING_HEADERS:
        ensure_booking_sheet_headers(sheet_id)
        rows = ws.get_all_values()
        if len(rows) < 2:
            return []
    out: List[Dict[str, Any]] = []
    for i in range(1, len(rows)):
        row_idx = i + 1
        r = rows[i]
        if not r or not any(str(c).strip() for c in r):
            continue
        cells = [str(r[j]).strip() if j < len(r) and r[j] is not None else "" for j in range(_N_COL)]
        bid, nm, ph, dt, tm, st, src, nts, created = cells
        if not bid and not nm:
            continue
        out.append(
            {
                "row_id": row_idx,
                "id": bid or str(uuid.uuid4()),
                "name": nm,
                "phone": ph,
                "date": dt,
                "time": tm,
                "status": st or "confirmed",
                "created_at": created or None,
                "source": src,
                "notes": nts,
            }
        )
    out.reverse()
    return out[:limit]


def _data_row_range_a1(row_id: int) -> str:
    if row_id < 2:
        raise ValueError("Row 1 is reserved for headers")
    end_col = chr(ord("A") + _N_COL - 1)
    return f"A{row_id}:{end_col}{row_id}"


def get_data_row_cells(sheet_id: str, row_id: int) -> List[str]:
    ensure_booking_sheet_headers(sheet_id)
    if row_id < 2:
        raise ValueError("Invalid row_id")
    ws = get_sheet(sheet_id)
    vals = ws.row_values(row_id)
    if not vals or not any(str(x).strip() for x in vals):
        raise LookupError("empty_row")
    return [str(vals[j]).strip() if j < len(vals) and vals[j] is not None else "" for j in range(_N_COL)]


def patch_booking_data_row(
    sheet_id: str,
    row_id: int,
    *,
    date: Optional[str] = None,
    time: Optional[str] = None,
    status: Optional[str] = None,
    name: Optional[str] = None,
    phone: Optional[str] = None,
    notes: Optional[str] = None,
) -> None:
    cells = get_data_row_cells(sheet_id, row_id)
    bid, nm, ph, dt, tm, st, src, nts, created = cells
    if date is not None:
        dt = date.strip()
    if time is not None:
        tm = time.strip()
    if status is not None:
        st = status.strip()
    if name is not None:
        nm = name.strip()
    if phone is not None:
        ph = phone.strip()
    if notes is not None:
        nts = notes.strip()
    new_row = [bid, nm, ph, dt, tm, st, src, nts, created]
    ws = get_sheet(sheet_id)
    ws.update(_data_row_range_a1(row_id), [new_row], value_input_option="RAW")


def delete_booking_data_row(sheet_id: str, row_id: int) -> None:
    ensure_booking_sheet_headers(sheet_id)
    if row_id < 2:
        raise ValueError("Invalid row_id")
    ws = get_sheet(sheet_id)
    ws.delete_rows(row_id)
