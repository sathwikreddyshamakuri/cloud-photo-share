import os

EMAIL_MODE = os.getenv("EMAIL_MODE", "console").lower().strip()

def send_email(to: str, subject: str, html: str, reply_to: str | None = None):
    """
    EMAIL_MODE:
      - console      : print to stdout (demo)
      - resend_test  : Resend test sender/recipient (no domain needed)
      - resend       : real sending via Resend (needs verified domain + EMAIL_SENDER)
    """
    if EMAIL_MODE == "console":
        print("\n--- DEV EMAIL (console) ---")
        print("TO:", to)
        print("SUBJECT:", subject)
        print("HTML:", html[:500], "..." if len(html) > 500 else "")
        if reply_to: print("REPLY-TO:", reply_to)
        print("--- END DEV EMAIL ---\n")
        return {"id": "dev-console", "mode": "console"}

    try:
        import resend  # type: ignore
    except Exception as e:
        raise RuntimeError("Install the 'resend' package in your venv: pip install resend") from e

    api_key = os.getenv("RESEND_API_KEY")
    if not api_key:
        raise RuntimeError("RESEND_API_KEY not set")
    resend.api_key = api_key

    if EMAIL_MODE == "resend_test":
        data = {
            "from": "Acme <onboarding@resend.dev>",
            "to": ["delivered@resend.dev"],
            "subject": subject or "Test email",
            "html": html or "<p>hello</p>",
        }
        if reply_to:
            data["reply_to"] = reply_to
        return resend.Emails.send(data)

    if EMAIL_MODE == "resend":
        sender = os.getenv("EMAIL_SENDER")  # e.g., 'Cloud Photo Share <no-reply@send.yourdomain.com>'
        if not sender:
            raise RuntimeError("EMAIL_SENDER is required in resend mode")
        data = {"from": sender, "to": [to], "subject": subject, "html": html}
        if reply_to:
            data["reply_to"] = reply_to
        return resend.Emails.send(data)

    raise RuntimeError(f"Unknown EMAIL_MODE={EMAIL_MODE!r}")
