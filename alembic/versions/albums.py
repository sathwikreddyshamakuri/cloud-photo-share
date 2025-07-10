
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from db import get_session
from models import Album
from deps import get_current_user   # <-- your existing JWT helper

router = APIRouter(prefix="/albums", tags=["albums"])

@router.get("/", response_model=list[Album])
def list_albums(
    session: Session = Depends(get_session),
    user = Depends(get_current_user)
):
    stmt = select(Album).where(Album.owner_id == user.id)
    return session.exec(stmt).all()

@router.post("/", response_model=Album, status_code=status.HTTP_201_CREATED)
def create_album(
    title: str,
    session: Session = Depends(get_session),
    user = Depends(get_current_user)
):
    album = Album(title=title, owner_id=user.id)
    session.add(album)
    session.commit()
    session.refresh(album)
    return album
