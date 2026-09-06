"""User schemas shared between auth, activity, and dashboard routers."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.common import PyObjectId


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserInDB(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: PyObjectId = Field(alias="_id")
    name: str
    email: EmailStr
    password_hash: str
    points: int = 0
    items_reused: int = 0
    items_recycled: int = 0
    items_disposed: int = 0
    waste_diverted: int = 0
    value_created_total_min: int = 0
    value_created_total_max: int = 0
    created_at: datetime


class PublicUser(BaseModel):
    id: str
    name: str
    email: EmailStr
    points: int
    items_reused: int
    items_recycled: int
    items_disposed: int
    waste_diverted: int
    value_created_total_min: int
    value_created_total_max: int


def public_user_from_doc(doc: dict) -> PublicUser:
    """Convert a users collection document into the public API shape."""
    return PublicUser(
        id=str(doc["_id"]),
        name=doc["name"],
        email=doc["email"],
        points=doc.get("points", 0),
        items_reused=doc.get("items_reused", 0),
        items_recycled=doc.get("items_recycled", 0),
        items_disposed=doc.get("items_disposed", 0),
        waste_diverted=doc.get("waste_diverted", 0),
        value_created_total_min=doc.get("value_created_total_min", 0),
        value_created_total_max=doc.get("value_created_total_max", 0),
    )


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: PublicUser