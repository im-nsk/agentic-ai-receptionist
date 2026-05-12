"""Apply additive schema updates (manual-first DB; no ORM create_all)."""

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def migrate_schema(engine: Engine) -> None:
    insp = inspect(engine)
    if not insp.has_table("clients"):
        return

    dialect = engine.dialect.name
    existing = {c["name"] for c in insp.get_columns("clients")}
    before = set(existing)

    additions: list[tuple[str, str]] = []

    if "email_verified" not in existing:
        additions.append(
            ("email_verified", "BOOLEAN NOT NULL DEFAULT TRUE" if dialect == "postgresql" else "INTEGER NOT NULL DEFAULT 1")
        )
    if "phone_number" not in existing:
        additions.append(("phone_number", "VARCHAR"))
    if "client_phone" not in existing:
        additions.append(("client_phone", "VARCHAR"))
    if "business_name" not in existing:
        additions.append(("business_name", "VARCHAR"))
    if "working_hours" not in existing:
        additions.append(("working_hours", "VARCHAR"))
    if "slot_duration" not in existing:
        additions.append(("slot_duration", "INTEGER DEFAULT 30"))
    if "services_json" not in existing:
        additions.append(("services_json", "TEXT"))
    if "free_text" not in existing:
        additions.append(("free_text", "TEXT"))

    if "otp_code" not in existing:
        additions.append(("otp_code", "TEXT"))
    if "otp_expiry" not in existing:
        additions.append(("otp_expiry", "TIMESTAMP"))
    if "is_verified" not in existing:
        additions.append(
            ("is_verified", "BOOLEAN NOT NULL DEFAULT FALSE" if dialect == "postgresql" else "INTEGER NOT NULL DEFAULT 0")
        )
    if "password_reset_otp" not in existing:
        additions.append(("password_reset_otp", "TEXT"))
    if "password_reset_otp_expiry" not in existing:
        additions.append(("password_reset_otp_expiry", "TIMESTAMP"))

    stmts = []
    for name, ctype in additions:
        if dialect == "postgresql":
            stmts.append(f"ALTER TABLE clients ADD COLUMN IF NOT EXISTS {name} {ctype}")
        else:
            stmts.append(f"ALTER TABLE clients ADD COLUMN {name} {ctype}")

    if stmts:
        with engine.begin() as conn:
            for stmt in stmts:
                conn.execute(text(stmt))

    insp2 = inspect(engine)
    cols = {c["name"] for c in insp2.get_columns("clients")}
    with engine.begin() as conn:
        _backfill_clients(conn, cols, dialect, before)


def _backfill_clients(conn, cols: set, dialect: str, before: set) -> None:
    if "email_verified" in cols and dialect != "postgresql":
        conn.execute(text("UPDATE clients SET email_verified = 1 WHERE email_verified IS NULL"))

    if "is_verified" in cols and "is_verified" not in before:
        if dialect == "postgresql":
            conn.execute(text("UPDATE clients SET is_verified = true"))
        else:
            conn.execute(text("UPDATE clients SET is_verified = 1"))

    if "phone_number" in cols and "phone" in before:
        conn.execute(text("UPDATE clients SET phone_number = phone WHERE phone_number IS NULL AND phone IS NOT NULL"))
