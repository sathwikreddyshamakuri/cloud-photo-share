# app/emailer.py
import os
import boto3

SES_REGION   = os.getenv("SES_REGION", os.getenv("REGION", "us-east-1"))
EMAIL_SENDER = os.getenv("EMAIL_SENDER", "no-reply@example.com")

_ses = boto3.client("ses", region_name=SES_REGION)

def send_email(to: str, subject: str, html: str, text: str | None = None):
    """Send using SES. If it fails (dev), just print."""
    try:
        _ses.send_email(
            Source=EMAIL_SENDER,
            Destination={"ToAddresses": [to]},
            Message={
                "Subject": {"Data": subject},
                "Body": {
                    "Text": {"Data": text or ""},
                    "Html": {"Data": html},
                },
            },
        )
    except Exception as e:
        # Local/dev fallback
        print("=== EMAIL Fallback ===")
        print("To:", to)
        print("Subj:", subject)
        print("Body:", html)
        print("Err:", e)
