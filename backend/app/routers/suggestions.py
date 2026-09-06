"""Suggestion routes: personalised DIY 'create value' ideas for a given scan."""

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.security import get_current_user
from app.db.mongodb import get_db
from app.models.user import UserInDB
from app.models.waste_scan import AIClassification
from app.services import nim_client
from app.services.suggestion_service import generate_create_ideas

router = APIRouter()


@router.get("/scan/{scan_id}/ideas")
async def get_create_ideas(
    scan_id: str,
    db=Depends(get_db),
    current_user: UserInDB = Depends(get_current_user),
    refresh: bool = Query(default=False),
):
    """Return DIY ideas for a scan. Empty idea list when the item needs special handling."""
    try:
        oid = ObjectId(scan_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid scan id")

    doc = await db["waste_scans"].find_one({"_id": oid, "user_id": ObjectId(current_user.id)})
    if doc is None:
        raise HTTPException(status_code=404, detail="Scan not found")

    classification = AIClassification(**doc["ai_result"])

    try:
        result = await generate_create_ideas(classification, db, force_refresh=refresh)
    except nim_client.NimError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return {"scan_id": str(oid), "label": doc["final_label"], "ideas": result["ideas"]}