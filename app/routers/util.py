from fastapi import APIRouter
from pydantic import BaseModel, EmailStr
from app.emailer import send_email

router = APIRouter(prefix="/util", tags=["util"])

class TestEmailIn(BaseModel):
    to: EmailStr | None = None

@router.post("/test-email")
def test_email(p: TestEmailIn):
    r = send_email(
        p.to or "demo@example.com",
        "Cloud Photo Share — Test Email",
        "<h2>It works 🎉</h2><p>Resend test mode.</p>",
    )
    return {"ok": True, "id": getattr(r, "id", str(r))}
