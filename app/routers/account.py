# app/routers/account.py
from fastapi import APIRouter, Depends
from ..auth import (
    ForgotIn, ResetIn, VerifyIn, ChangePwdIn,
    forgot_password, reset_password, verify_email,
    change_password, current_user
)

router = APIRouter(prefix="/auth", tags=["auth-extra"])

@router.post("/forgot")
def forgot(body: ForgotIn):
    return forgot_password(body)

@router.post("/reset")
def reset(body: ResetIn):
    return reset_password(body)

@router.post("/verify")
def verify(body: VerifyIn):
    return verify_email(body)

@router.put("/password")
def change_pwd(data: ChangePwdIn, user_id: str = Depends(current_user)):
    return change_password(user_id, data)
