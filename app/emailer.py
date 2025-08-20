# app/emailer.py
import os

try:
    import resend  # pip install resend
except Exception:  # pragma: no cover
    resend = None  # allows tests/CI to run without the lib

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "No-Reply <noreply@localhost>")

def send_email(to: str, subject: str, html: str) -> dict:
    """
    Sends an email via Resend. In CI/dev with no API key, it no-ops cleanly.
    """
    if not RESEND_API_KEY or resend is None:
        # No key or library: behave as a no-op so tests don't fail.
        return {"skipped": True, "to": to, "subject": subject}

    resend.api_key = RESEND_API_KEY
    return resend.Emails.send({
        "from": EMAIL_FROM,
        "to": [to],
        "subject": subject,
        "html": html,
    })

def verification_email_html(verify_url: str) -> str:
    return f"""
      <h2>Verify your email</h2>
      <p>Click the button below to verify your account.</p>
      <p><a href="{verify_url}" style="display:inline-block;padding:10px 16px;border-radius:6px;background:#111;color:#fff;text-decoration:none">Verify Email</a></p>
      <p>If the button doesn’t work, open this link:<br>{verify_url}</p>
    """

def reset_email_html(reset_url: str) -> str:
    return f"""
      <h2>Reset your password</h2>
      <p>We received a request to reset your password.</p>
      <p><a href="{reset_url}" style="display:inline-block;padding:10px 16px;border-radius:6px;background:#111;color:#fff;text-decoration:none">Reset Password</a></p>
      <p>If you didn’t request this, you can ignore this email.<br>Direct link: {reset_url}</p>
    """
