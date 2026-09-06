"""Activity routes: confirm 'made / recycled / disposed' and earn points."""

from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import get_current_user
from app.db.mongodb import get_db
from app.models.user import UserInDB
from app.services import points_service

router = APIRouter()


async def _valid_scans(db, scan_id: str, user_id: str, action_type: str, requires_special: Optional[bool]):
    try:
        oid = ObjectId(scan_id)
        user_oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    scan = await db["waste_scans"].find_one({"_id": oid, "user_id": user_oid})
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    if requires_special is not None and scan.get("requires_special_handling"):
        raise HTTPException(status_code=400, detail="This item requires special handling")
    return scan


@router.post("/activity/made")
async def mark_made(
    scan_id: str,
    value_min: Optional[int] = None,
    value_max: Optional[int] = None,
    db=Depends(get_db),
    current_user: UserInDB = Depends(get_current_user),
):
    await _valid_scans(db, scan_id, current_user.id, "made_item", requires_special=False)
    try:
        result = await points_service.award_points(
            db,
            current_user.id,
            scan_id,
            "made_item",
            value_created_min=value_min,
            value_created_max=value_max,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return {"message": "Great job! You gave waste a second life. 🎉", **result}


@router.post("/activity/recycled")
async def mark_recycled(
    scan_id: str,
    recycler_id: Optional[str] = None,
    db=Depends(get_db),
    current_user: UserInDB = Depends(get_current_user),
):
    await _valid_scans(db, scan_id, current_user.id, "recycled_item", requires_special=None)
    try:
        result = await points_service.award_points(
            db,
            current_user.id,
            scan_id,
            "recycled_item",
            recycler_id=recycler_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return {"message": "Thanks for recycling responsibly! ♻️", **result}


@router.post("/activity/disposed")
async def mark_disposed(
    scan_id: str,
    db=Depends(get_db),
    current_user: UserInDB = Depends(get_current_user),
):
    await _valid_scans(db, scan_id, current_user.id, "disposed_item", requires_special=None)
    try:
        result = await points_service.award_points(
            db,
            current_user.id,
            scan_id,
            "disposed_item",
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return {"message": "Thank you for disposing responsibly! 🗑️", **result}