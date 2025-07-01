from datetime import datetime
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    password_hash: str
    albums: List["Album"] = Relationship(back_populates="owner")

class Album(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    owner_id: int = Field(foreign_key="user.id")
    owner: User = Relationship(back_populates="albums")
    photos: List["Photo"] = Relationship(back_populates="album")

class Photo(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    filename: str
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    album_id: int = Field(foreign_key="album.id")
    width: Optional[int] = None
    height: Optional[int] = None
    taken_at: Optional[datetime] = None
    album: Album = Relationship(back_populates="photos")
