"""Transactional email (Resend). OTP never logged in production when unconfigured."""

import os

_DEFAULT_FROM = "onboarding@resend.dev"


def _devish() -> bool:
    env = (os.getenv("ENVIRONMENT") or os.getenv("ENV") or "development").lower()
    return env in ("dev", "development", "local", "test")


def _resend_from() -> str:
    return (os.getenv("RESEND_FROM") or _DEFAULT_FROM).strip() or _DEFAULT_FROM


def send_email_otp(email: str, otp: str) -> None:
    """Send signup / email verification OTP via Resend. Dev-only console fallback when unconfigured."""
    api_key = os.getenv("RESEND_API_KEY", "").strip()
    from_addr = _resend_from()

    if not api_key:
        if _devish():
            print(f"[DEV] RESEND_API_KEY not set — signup OTP for {email}: {otp}")
        else:
            print(f"[EMAIL] RESEND_API_KEY not set — signup OTP not sent to {email}")
        return

    try:
        import resend  # type: ignore

        resend.api_key = api_key
        params: dict = {
            "from": from_addr,
            "to": [email],
            "subject": "Your verification code",
            "html": (
                f"<p>Your verification code is <strong>{otp}</strong>. "
                "It expires in 5 minutes.</p>"
            ),
        }
        resend.Emails.send(params)
    except Exception as e:  # noqa: BLE001 — never fail signup on email alone
        print(f"[EMAIL] Resend error: {e!r}")
        if _devish():
            print(f"[DEV] Signup OTP for {email}: {otp}")


def send_otp_email(to_email: str, code: str) -> None:
    """Backward-compatible alias for :func:`send_email_otp`."""
    send_email_otp(to_email, code)


def send_password_reset_email(to_email: str, code: str) -> None:
    api_key = os.getenv("RESEND_API_KEY", "").strip()
    from_addr = _resend_from()

    if not api_key:
        if _devish():
            print(f"[DEV] RESEND_API_KEY not set — password reset OTP for {to_email}: {code}")
        else:
            print(f"[EMAIL] RESEND_API_KEY not set — password reset OTP not sent to {to_email}")
        return

    try:
        import resend  # type: ignore

        resend.api_key = api_key
        params: dict = {
            "from": from_addr,
            "to": [to_email],
            "subject": "Reset your password",
            "html": (
                f"<p>Your password reset code is <strong>{code}</strong>. "
                "It expires in 5 minutes. If you did not request this, you can ignore this email.</p>"
            ),
        }
        resend.Emails.send(params)
    except Exception as e:  # noqa: BLE001
        print(f"[EMAIL] Resend password reset error: {e!r}")
        if _devish():
            print(f"[DEV] Password reset OTP for {to_email}: {code}")
