"""Auth routes: register, login (returns JWT), and current-user info."""

from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.db.mongodb import get_db
from app.models.user import AuthResponse, UserInDB, UserLogin, UserCreate, public_user_from_doc

router = APIRouter()


@router.post("/auth/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, db=Depends(get_db)):
    existing = await db["users"].find_one({"email": payload.email})
    if existing is not None:
        raise HTTPException(status_code=400, detail="An account with this email already exists")

    doc = {
        "name": payload.name,
        "email": payload.email,
        "password_hash": hash_password(payload.password),
        "points": 0,
        "items_reused": 0,
        "items_recycled": 0,
        "items_disposed": 0,
        "waste_diverted": 0,
        "value_created_total_min": 0,
        "value_created_total_max": 0,
        "created_at": datetime.now(timezone.utc),
    }
    result = await db["users"].insert_one(doc)
    doc["_id"] = result.inserted_id

    res = public_user_from_doc(doc)
    token = create_access_token(str(result.inserted_id))
    return AuthResponse(access_token=token, user=res)


@router.post("/auth/login", response_model=AuthResponse)
async def login(payload: UserLogin, db=Depends(get_db)):
    doc = await db["users"].find_one({"email": payload.email})
    if doc is None or not verify_password(payload.password, doc["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    res = public_user_from_doc(doc)
    token = create_access_token(str(doc["_id"]))
    return AuthResponse(access_token=token, user=res)


@router.get("/auth/me", response_model=UserInDB)
async def me(current_user: UserInDB = Depends(get_current_user)):
    return current_user