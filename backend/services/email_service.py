"""Transactional email (Resend). Falls back to console in dev when unconfigured."""

import os


def send_otp_email(to_email: str, code: str) -> None:
    api_key = os.getenv("RESEND_API_KEY", "").strip()
    from_addr = os.getenv("RESEND_FROM", "AI Receptionist <onboarding@resend.dev>")
    env = (os.getenv("ENVIRONMENT") or os.getenv("ENV") or "development").lower()
    devish = env in ("dev", "development", "local", "test")

    if not api_key:
        if devish:
            print(f"[DEV] RESEND_API_KEY not set — OTP for {to_email}: {code}")
        else:
            print(f"[EMAIL] RESEND_API_KEY not set — OTP not sent to {to_email}")
        return

    try:
        import resend  # type: ignore

        resend.api_key = api_key
        params: dict = {
            "from": from_addr,
            "to": [to_email],
            "subject": "Your verification code",
            "html": (
                f"<p>Your verification code is <strong>{code}</strong>. "
                "It expires in 5 minutes.</p>"
            ),
        }
        resend.Emails.send(params)
    except Exception as e:  # noqa: BLE001 — never fail signup on email alone
        env = (os.getenv("ENVIRONMENT") or os.getenv("ENV") or "development").lower()
        devish = env in ("dev", "development", "local", "test")
        print(f"[EMAIL] Resend error: {e!r}")
        if devish:
            print(f"[DEV] OTP for {to_email}: {code}")
