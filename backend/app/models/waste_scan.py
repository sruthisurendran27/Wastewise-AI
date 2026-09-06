"""Waste scan schemas: AI classification, stored scan documents, correction input."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

CATEGORY_VALUES = [
    "Recyclable",
    "Reusable",
    "Organic/Compostable",
    "Hazardous/Special",
    "General Waste",
]
PATH_VALUES = ["create", "recycle", "dispose"]
STATUS_VALUES = ["analyzed", "path_chosen", "completed"]


class AIClassification(BaseModel):
    label: str
    material: str
    category: str
    condition: str
    requires_special_handling: bool = False
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    raw_model_text: str = ""


class WasteScanOut(BaseModel):
    id: str
    image_url: Optional[str] = None
    ai_result: AIClassification
    user_corrected_label: Optional[str] = None
    final_label: str
    category: str
    requires_special_handling: bool
    chosen_path: Optional[str] = None
    status: str
    created_at: datetime


class ScanCorrectionIn(BaseModel):
    label: str = Field(min_length=1, max_length=200)
    category: Optional[str] = Field(default=None)
    material: Optional[str] = Field(default=None)


class ScanFeedbackIn(BaseModel):
    helpful: bool
    issue: Optional[str] = Field(default=None, max_length=80)


def scan_doc_to_out(doc: dict) -> WasteScanOut:
    return WasteScanOut(
        id=str(doc["_id"]),
        image_url=doc.get("image_url"),
        ai_result=AIClassification(**doc["ai_result"]),
        user_corrected_label=doc.get("user_corrected_label"),
        final_label=doc.get("final_label", doc["ai_result"]["label"]),
        category=doc.get("category", doc["ai_result"]["category"]),
        requires_special_handling=doc.get(
            "requires_special_handling", doc["ai_result"].get("requires_special_handling", False)
        ),
        chosen_path=doc.get("chosen_path"),
        status=doc.get("status", "analyzed"),
        created_at=doc["created_at"],
    )
