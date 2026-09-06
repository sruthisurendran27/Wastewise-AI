"""Disposal routes: curated guidance for items needing special handling.

Deliberately served from a curated seed dataset rather than free-form AI output so
that safety-critical instructions are deterministic and trustworthy.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from app.core.security import get_current_user
from app.db.mongodb import get_db
from app.models.user import UserInDB

router = APIRouter()


@router.get("/disposal")
async def disposal_guide(
    waste_type: Optional[str] = None,
    db=Depends(get_db),
    current_user: UserInDB = Depends(get_current_user),
):
    """Return the disposal guide(s) matching a waste type, or all guides."""
    query = {"waste_type": waste_type} if waste_type else {}
    docs = []
    async for doc in db["disposal_guides"].find(query):
        doc["id"] = str(doc["_id"])
        del doc["_id"]
        docs.append(doc)
    if waste_type and not docs:
        raise HTTPException(status_code=404, detail="No disposal guide found for this waste type")
    return {"guides": docs}