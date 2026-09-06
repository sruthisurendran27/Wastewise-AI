"""Scan routes: upload+classify an image, fetch a scan, correct a misclassification."""

from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.core.config import settings
from app.core.security import get_current_user
from app.db.mongodb import get_db
from app.models.user import UserInDB
from app.models.waste_scan import (
    AIClassification,
    ScanCorrectionIn,
    ScanFeedbackIn,
    WasteScanOut,
    CATEGORY_VALUES,
    scan_doc_to_out,
)
from app.services.classification_service import classify_waste
from app.services.nim_client import NimError
from app.utils.image_utils import save_upload

router = APIRouter()


async def _get_user_scan(db, scan_id: str, user_id: str) -> tuple[ObjectId, dict]:
    try:
        oid = ObjectId(scan_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid scan id")
    doc = await db["waste_scans"].find_one({"_id": oid, "user_id": ObjectId(user_id)})
    if doc is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    return oid, doc


@router.post("/scan", response_model=WasteScanOut, status_code=status.HTTP_201_CREATED)
async def upload_scan(
    file: UploadFile = File(...),
    db=Depends(get_db),
    current_user: UserInDB = Depends(get_current_user),
):
    public_url, abs_path = save_upload(file, settings.upload_dir)

    try:
        classification: AIClassification = await classify_waste(abs_path)
    except NimError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    doc = {
        "user_id": ObjectId(current_user.id),
        "image_url": public_url,
        "abs_path": abs_path,
        "ai_result": classification.model_dump(),
        "user_corrected_label": None,
        "final_label": classification.label,
        "category": classification.category,
        "requires_special_handling": classification.requires_special_handling,
        "chosen_path": None,
        "status": "analyzed",
        "created_at": datetime.now(timezone.utc),
    }
    result = await db["waste_scans"].insert_one(doc)
    doc["_id"] = result.inserted_id
    return scan_doc_to_out(doc)


@router.get("/scan/{scan_id}", response_model=WasteScanOut)
async def get_scan(
    scan_id: str,
    db=Depends(get_db),
    current_user: UserInDB = Depends(get_current_user),
):
    _, doc = await _get_user_scan(db, scan_id, current_user.id)
    return scan_doc_to_out(doc)


@router.get("/scans", response_model=list[WasteScanOut])
async def list_scans(
    limit: int = 30,
    db=Depends(get_db),
    current_user: UserInDB = Depends(get_current_user),
):
    """Return the user's recent scans for the history view."""
    limit = max(1, min(limit, 100))
    cursor = db["waste_scans"].find({"user_id": ObjectId(current_user.id)}).sort("created_at", -1).limit(limit)
    return [scan_doc_to_out(doc) async for doc in cursor]


@router.post("/scan/{scan_id}/feedback")
async def scan_feedback(
    scan_id: str,
    payload: ScanFeedbackIn,
    db=Depends(get_db),
    current_user: UserInDB = Depends(get_current_user),
):
    oid, _ = await _get_user_scan(db, scan_id, current_user.id)
    await db["scan_feedback"].insert_one({
        "user_id": ObjectId(current_user.id),
        "scan_id": oid,
        "helpful": payload.helpful,
        "issue": payload.issue,
        "created_at": datetime.now(timezone.utc),
    })
    return {"message": "Thanks for helping improve WasteWise."}


@router.patch("/scan/{scan_id}/correct", response_model=WasteScanOut)
async def correct_scan(
    scan_id: str,
    payload: ScanCorrectionIn,
    db=Depends(get_db),
    current_user: UserInDB = Depends(get_current_user),
):
    oid, doc = await _get_user_scan(db, scan_id, current_user.id)

    category = payload.category or doc["ai_result"].get("category", "General Waste")
    if category not in CATEGORY_VALUES:
        raise HTTPException(status_code=400, detail=f"Invalid category: {category}")

    special = doc["ai_result"].get("requires_special_handling", False)
    if category == "Hazardous/Special":
        special = True

    update = {
        "$set": {
            "user_corrected_label": payload.label,
            "final_label": payload.label,
            "category": category,
            "ai_result.label": payload.label,
            "ai_result.material": payload.material if payload.material else doc["ai_result"].get("material", ""),
            "ai_result.category": category,
            "requires_special_handling": special,
        }
    }
    await db["waste_scans"].update_one({"_id": oid}, update)
    doc = await db["waste_scans"].find_one({"_id": oid})
    return scan_doc_to_out(doc)
