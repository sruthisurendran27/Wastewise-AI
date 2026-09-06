"""Points & impact service: atomic stat updates and activity ledger entries."""

from bson import ObjectId
from datetime import datetime, timezone
from typing import List, Optional

from app.models.activity import DashboardStats, POINTS_BY_ACTION, activity_doc_to_out


def _oid(user_id: str) -> ObjectId:
    """Convert a string user id to ObjectId for Mongo queries."""
    if isinstance(user_id, ObjectId):
        return user_id
    try:
        return ObjectId(user_id)
    except Exception:
        # Allow plain string ids in tests / edge cases.
        return user_id  # type: ignore[return-value]


async def check_duplicate_activity(db, scan_id: str, action_type: str) -> bool:
    """Return True if the scan has already recorded this action type."""
    return await db["activities"].find_one(
        {"scan_id": _oid(scan_id), "action_type": action_type}
    ) is not None


async def award_points(
    db,
    user_id: str,
    scan_id: str,
    action_type: str,
    value_created_min: Optional[int] = None,
    value_created_max: Optional[int] = None,
    recycler_id: Optional[str] = None,
) -> dict:
    """
    Record a completed action for a scan and atomically credit the user.

    Guards against double-crediting the same scan for the same action type.
    """
    if action_type not in POINTS_BY_ACTION:
        raise ValueError(f"Unknown action type: {action_type}")

    if await check_duplicate_activity(db, scan_id, action_type):
        raise ValueError("Action already recorded for this scan")

    user_oid = _oid(user_id)
    scan_oid = _oid(scan_id)

    if not isinstance(scan_oid, ObjectId) or not isinstance(user_oid, ObjectId):
        raise ValueError("Invalid user or scan id")

    points = POINTS_BY_ACTION[action_type]
    update: dict = {"$inc": {"points": points}}

    if action_type == "made_item":
        update["$inc"]["items_reused"] = 1
        update["$inc"]["waste_diverted"] = 1
        if value_created_min is not None:
            update["$inc"]["value_created_total_min"] = int(value_created_min)
        if value_created_max is not None:
            update["$inc"]["value_created_total_max"] = int(value_created_max)
    elif action_type == "recycled_item":
        update["$inc"]["items_recycled"] = 1
        update["$inc"]["waste_diverted"] = 1
    elif action_type == "disposed_item":
        update["$inc"]["items_disposed"] = 1
        update["$inc"]["waste_diverted"] = 1

    await db["users"].update_one({"_id": user_oid}, update)

    description = {
        "made_item": "Made something new from waste 💡",
        "recycled_item": "Recycled an item ♻️",
        "disposed_item": "Disposed of an item responsibly 🗑️",
    }[action_type]

    now = datetime.now(timezone.utc)
    activity = {
        "user_id": user_oid,
        "scan_id": scan_oid,
        "action_type": action_type,
        "points_earned": points,
        "value_created_min": value_created_min,
        "value_created_max": value_created_max,
        "recycler_id": recycler_id,
        "description": description,
        "created_at": now,
    }
    result = await db["activities"].insert_one(activity)
    activity["_id"] = result.inserted_id
    return {"points_earned": points, "activity": activity_doc_to_out(activity)}


async def get_dashboard_stats(db, user_id: str) -> DashboardStats:
    """Aggregate a user's profile counters plus the most recent activity entries."""
    user = await db["users"].find_one({"_id": _oid(user_id)})
    if user is None:
        raise ValueError("User not found")

    activities: List[dict] = []
    user_oid = _oid(user_id)
    cursor = (
        db["activities"]
        .find({"user_id": user_oid})
        .sort("created_at", -1)
        .limit(10)
    )
    async for doc in cursor:
        activities.append(activity_doc_to_out(doc))

    return DashboardStats(
        points=user.get("points", 0),
        items_reused=user.get("items_reused", 0),
        items_recycled=user.get("items_recycled", 0),
        items_disposed=user.get("items_disposed", 0),
        waste_diverted=user.get("waste_diverted", 0),
        value_created_total_min=user.get("value_created_total_min", 0),
        value_created_total_max=user.get("value_created_total_max", 0),
        recent_activities=activities,
    )