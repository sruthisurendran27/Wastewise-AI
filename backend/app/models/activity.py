"""Activity & dashboard schemas for points/impact tracking."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

ACTION_TYPES = ["made_item", "recycled_item", "disposed_item"]
# Points awarded per action type - keep in sync with frontend expectations.
POINTS_BY_ACTION = {"made_item": 20, "recycled_item": 15, "disposed_item": 10}


class ActivityDoc(BaseModel):
    _id: str
    user_id: str
    scan_id: str
    action_type: str
    points_earned: int
    value_created_min: Optional[int] = None
    value_created_max: Optional[int] = None
    description: str = ""
    recycler_id: Optional[str] = None
    created_at: datetime


class ActivityOut(BaseModel):
    id: str
    action_type: str
    points_earned: int
    description: str
    created_at: datetime


class DashboardStats(BaseModel):
    points: int
    items_reused: int
    items_recycled: int
    items_disposed: int
    waste_diverted: int
    value_created_total_min: int
    value_created_total_max: int
    recent_activities: List[ActivityOut]


def activity_doc_to_out(doc: dict) -> ActivityOut:
    return ActivityOut(
        id=str(doc["_id"]),
        action_type=doc["action_type"],
        points_earned=doc["points_earned"],
        description=doc.get("description", ""),
        created_at=doc["created_at"],
    )