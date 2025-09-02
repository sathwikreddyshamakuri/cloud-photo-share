# app/routers/account.py
from fastapi import APIRouter, Depends, status
from ..auth import current_user

router = APIRouter(prefix="/account", tags=["account"])

@router.get("/me")
def get_me(user_id: str = Depends(current_user)):
    return {"user_id": user_id}

@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(user_id: str = Depends(current_user)):
    # TODO: implement data deletion if needed
    return
