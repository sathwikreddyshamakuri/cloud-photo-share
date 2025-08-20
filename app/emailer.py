# app/emailer.py
import os

try:
    import resend  # pip install resend
except Exception:  # pragma: no cover
    resend = None  # allow tests/CI without the lib

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "No-Reply <noreply@localhost>")

__all__ = ["send_email", "verification_email_html", "reset_email_html"]


def send_email(to: str, subject: str, html: str) -> dict:
    """
    Send an email via Resend.
    If EMAIL_MODE=console, print to stdout and return {"mode": "console", ...}.
    If no API key (CI/dev), no-op cleanly.
    """
    email_mode = os.getenv("EMAIL_MODE", "").strip().lower()

    # Console mode: used by tests (tests/test_emailer_console.py)
    if email_mode == "console":
        print("=== EMAIL (console) ===")
        print(f"To: {to}")
        print(f"Subject: {subject}")
        print("HTML:")
        print(html)
        print("=======================")
        return {"mode": "console", "to": to, "subject": subject}


    if not RESEND_API_KEY or resend is None:
        return {"skipped": True, "to": to, "subject": subject}

    # Real send via Resend
    resend.api_key = RESEND_API_KEY
    return resend.Emails.send({
        "from": EMAIL_FROM,
        "to": [to],
        "subject": subject,
        "html": html,
    })



def verification_email_html(verify_url: str) -> str:
    btn_style = (
        "display:inline-block;padding:10px 16px;border-radius:6px;"
        "background:#111;color:#fff;text-decoration:none"
    )
    return (
        "<h2>Verify your email</h2>"
        "<p>Click the button below to verify your account.</p>"
        f'<p><a href="{verify_url}" style="{btn_style}">Verify Email</a></p>'
        f"<p>If the button doesn’t work, open this link:<br>{verify_url}</p>"
    )


def reset_email_html(reset_url: str) -> str:
    btn_style = (
        "display:inline-block;padding:10px 16px;border-radius:6px;"
        "background:#111;color:#fff;text-decoration:none"
    )
    return (
        "<h2>Reset your password</h2>"
        "<p>We received a request to reset your password.</p>"
        f'<p><a href="{reset_url}" style="{btn_style}">Reset Password</a></p>'
        "<p>If you didn’t request this, you can ignore this email.</p>"
        f"<p>Direct link: {reset_url}</p>"
    )
