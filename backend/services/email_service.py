"""Transactional email via Resend (signup OTP, password reset).

Production requirements (Resend dashboard):
  1. Add and verify your domain: https://resend.com/domains
  2. Set RESEND_API_KEY (starts with re_)
  3. Set RESEND_FROM to an address on that verified domain, e.g.:
       RESEND_FROM="AI Receptionist <noreply@yourdomain.com>"

Do NOT use onboarding@resend.dev in production — it only delivers to your Resend account email.
"""

from __future__ import annotations

import os
import re
from typing import Optional

_RESEND_TEST_DOMAIN = "wrixio.com"
_DEFAULT_FROM = "noreply@wrixio.com"
_EMAIL_IN_FROM = re.compile(r"<([^>]+@[^>]+)>")
_PLAIN_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class EmailConfigurationError(Exception):
    """Resend is misconfigured for the current environment."""


class EmailDeliveryError(Exception):
    """Resend API rejected or failed to send the message."""

    def __init__(self, message: str, *, recipient: str, cause: Optional[BaseException] = None):
        super().__init__(message)
        self.recipient = recipient
        self.cause = cause


def _devish() -> bool:
    for key in ("ENVIRONMENT", "ENV", "APP_ENV"):
        env = (os.getenv(key) or "").lower()
        if env in ("dev", "development", "local", "test"):
            return True
        if env in ("production", "prod"):
            return False
    return True


def _is_production() -> bool:
    return not _devish()


def _extract_email_address(from_value: str) -> str:
    """Parse bare or display-formatted From value."""
    raw = (from_value or "").strip()
    angle = _EMAIL_IN_FROM.search(raw)
    if angle:
        return angle.group(1).strip().lower()
    return raw.lower()


def _from_domain(from_value: str) -> str:
    addr = _extract_email_address(from_value)
    if "@" not in addr:
        return ""
    return addr.split("@", 1)[1].lower()


def is_resend_test_sender(from_value: Optional[str] = None) -> bool:
    """True when using Resend's sandbox From domain (external recipients blocked)."""
    domain = _from_domain(from_value or resend_from())
    return domain == _RESEND_TEST_DOMAIN or domain.endswith(f".{_RESEND_TEST_DOMAIN}")


def resend_from() -> str:
    return (os.getenv("RESEND_FROM") or _DEFAULT_FROM).strip() or _DEFAULT_FROM


def resend_api_key() -> str:
    return (os.getenv("RESEND_API_KEY") or "").strip()


def validate_resend_for_production() -> list[str]:
    """Return human-readable configuration problems (empty if OK)."""
    problems: list[str] = []
    if not resend_api_key():
        problems.append("RESEND_API_KEY is not set.")
    from_addr = resend_from()
    if is_resend_test_sender(from_addr):
        problems.append(
            f'RESEND_FROM={from_addr!r} uses Resend test mail (resend.dev). '
            "Verify your domain at https://resend.com/domains and set RESEND_FROM "
            'to an address on that domain, e.g. "AI Receptionist <noreply@yourdomain.com>".'
        )
    elif not _PLAIN_EMAIL.match(_extract_email_address(from_addr)) and "<" not in from_addr:
        problems.append(f"RESEND_FROM={from_addr!r} does not look like a valid email address.")
    return problems


def log_resend_startup_status() -> None:
    """Log Resend readiness once at process start."""
    from_addr = resend_from()
    has_key = bool(resend_api_key())
    if _is_production():
        problems = validate_resend_for_production()
        if problems:
            print("[EMAIL] Production Resend misconfiguration:")
            for p in problems:
                print(f"  - {p}")
        else:
            print(f"[EMAIL] Resend ready (production). from={from_addr!r}")
    else:
        mode = "test sender (external recipients blocked)" if is_resend_test_sender() else "custom domain"
        print(
            f"[EMAIL] Resend dev mode. api_key={'set' if has_key else 'missing'}, "
            f"from={from_addr!r}, {mode}"
        )


def _ensure_can_send_to(recipient: str) -> None:
    recipient = recipient.strip().lower()
    if not recipient:
        raise EmailDeliveryError("Recipient email is required.", recipient=recipient)

    api_key = resend_api_key()
    from_addr = resend_from()

    if not api_key:
        if _devish():
            return
        raise EmailConfigurationError(
            "RESEND_API_KEY is not set. Add your Resend API key to the server environment."
        )

    if _is_production() and is_resend_test_sender(from_addr):
        raise EmailConfigurationError(
            "RESEND_FROM uses onboarding@resend.dev (or another @resend.dev address). "
            "That sender only works for your Resend account email. "
            "Verify a domain at https://resend.com/domains and set RESEND_FROM to "
            'e.g. "AI Receptionist <noreply@yourdomain.com>".'
        )


def _format_resend_error(exc: BaseException, *, recipient: str, from_addr: str) -> str:
    msg = str(exc).strip()
    lower = msg.lower()
    if "testing emails" in lower or "verify a domain" in lower:
        return (
            "Email provider is in test mode: sender must use your verified domain, not @resend.dev. "
            "Set RESEND_FROM on Render to an address from a domain verified at resend.com/domains."
        )
    if "domain" in lower and ("not verified" in lower or "verify" in lower):
        return (
            f"Sender domain for {from_addr!r} is not verified in Resend. "
            "Complete DNS verification at https://resend.com/domains."
        )
    return f"Could not send email to {recipient}."


def _send_html_email(*, to_email: str, subject: str, html: str) -> None:
    to_email = to_email.strip().lower()
    _ensure_can_send_to(to_email)

    api_key = resend_api_key()
    from_addr = resend_from()

    if not api_key:
        if _devish():
            print(f"[DEV] RESEND_API_KEY not set — email to {to_email} not sent (subject={subject!r})")
        return

    try:
        import resend  # type: ignore

        resend.api_key = api_key
        params: dict = {
            "from": from_addr,
            "to": [to_email],
            "subject": subject,
            "html": html,
        }
        reply_to = (os.getenv("RESEND_REPLY_TO") or "").strip()
        if reply_to:
            params["reply_to"] = [reply_to]

        result = resend.Emails.send(params)
        if isinstance(result, dict) and result.get("error"):
            err = result["error"]
            detail = err.get("message", err) if isinstance(err, dict) else str(err)
            raise EmailDeliveryError(
                _format_resend_error(Exception(detail), recipient=to_email, from_addr=from_addr),
                recipient=to_email,
            )
        print(f"[EMAIL] Sent {subject!r} to {to_email} (id={getattr(result, 'id', result)})")
    except EmailConfigurationError:
        raise
    except EmailDeliveryError:
        raise
    except Exception as exc:
        print(f"[EMAIL] Resend error to {to_email}: {exc!r}")
        raise EmailDeliveryError(
            _format_resend_error(exc, recipient=to_email, from_addr=from_addr),
            recipient=to_email,
            cause=exc,
        ) from exc


def send_email_otp(email: str, otp: str) -> None:
    """Send signup / email verification OTP. Raises on production delivery failure."""
    html = (
        f"<p>Your verification code is <strong>{otp}</strong>. "
        "It expires in 5 minutes.</p>"
    )
    try:
        _send_html_email(to_email=email, subject="Your verification code", html=html)
    except (EmailConfigurationError, EmailDeliveryError):
        if _devish():
            print(f"[DEV] Signup OTP for {email}: {otp}")
        raise


def send_otp_email(to_email: str, code: str) -> None:
    """Backward-compatible alias."""
    send_email_otp(to_email, code)


def send_password_reset_email(to_email: str, code: str) -> None:
    """Send password reset OTP. Raises on production delivery failure."""
    html = (
        f"<p>Your password reset code is <strong>{code}</strong>. "
        "It expires in 5 minutes. If you did not request this, you can ignore this email.</p>"
    )
    try:
        _send_html_email(to_email=to_email, subject="Reset your password", html=html)
    except (EmailConfigurationError, EmailDeliveryError):
        if _devish():
            print(f"[DEV] Password reset OTP for {to_email}: {code}")
        raise
