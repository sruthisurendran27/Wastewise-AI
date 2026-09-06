"""Authentication helpers: password hashing, JWT creation/validation, current-user dependency."""

from datetime import datetime, timedelta, timezone

from bson import ObjectId
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import ValidationError

from app.core.config import settings
from app.db.mongodb import get_db
from app.models.common import PyObjectId
from app.models.user import UserInDB

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

ALGORITHM = settings.jwt_algorithm
SECRET_KEY = settings.jwt_secret


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": user_id, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> str:
    """Return the user id (sub) contained in a valid token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        return user_id
    except (JWTError, ValidationError):
        raise credentials_exception


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db=Depends(get_db),
) -> UserInDB:
    user_id = decode_access_token(token)
    doc = await db["users"].find_one({"_id": ObjectId(user_id)})
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return UserInDB(**doc)