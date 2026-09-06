"""Recycler lookup service: MongoDB geospatial queries + distance formatting."""

from typing import List, Optional

from app.models.recycler import recycler_doc_to_out

EARTH_KM_PER_RADIAN = 6371.0


async def find_nearby(
    db,
    latitude: float,
    longitude: float,
    material: Optional[str] = None,
    type_filter: Optional[str] = None,
    district: Optional[str] = None,
    radius_km: float = 15.0,
    limit: int = 25,
) -> List[dict]:
    """
    Return recyclers within `radius_km` of (latitude, longitude), nearest first,
    optionally filtered by accepted material and/or facility type.

    Each returned item is a RecyclerOut-shaped dict including distance_km.
    """
    query: dict = {
        "location": {
            "$near": {
                "$geometry": {"type": "Point", "coordinates": [longitude, latitude]},
                "$maxDistance": radius_km * 1000,
            }
        }
    }
    if type_filter:
        query["type"] = type_filter
    if district:
        query["district"] = district

    # Directory labels vary from scan labels, so match material aliases in Python.
    cursor = db["recyclers"].find(query).limit(limit * 3 if material else limit)

    results = []
    async for doc in cursor:
        if material and not _material_matches(material, doc.get("accepted_materials", [])):
            continue
        distance_km = _distance_km(
            latitude, longitude, doc["location"]["coordinates"][1], doc["location"]["coordinates"][0]
        )
        results.append(recycler_doc_to_out(doc, distance_km=round(distance_km, 1)))
        if len(results) >= limit:
            break
    return results


def _material_matches(material: str, accepted_materials: list[str]) -> bool:
    """Match related labels such as 'Organic waste' and 'food scraps'."""
    query_words = set(material.lower().replace("/", " ").replace("-", " ").split())
    query_words.discard("waste")
    groups = (
        {"organic", "compost", "food", "fruit", "vegetable", "garden", "plant", "biodegradable"},
        {"plastic", "pet", "hdpe", "ldpe"},
        {"paper", "cardboard", "occ"},
        {"metal", "aluminium", "aluminum", "copper", "steel", "iron"},
        {"glass", "bottle", "jar"},
        {"e", "waste", "electronic", "battery", "circuit"},
        {"textile", "cloth", "clothing", "fabric"},
    )
    for accepted in accepted_materials:
        accepted_words = set(accepted.lower().replace("/", " ").replace("-", " ").split())
        accepted_words.discard("waste")
        if query_words & accepted_words:
            return True
        if any(query_words & group and accepted_words & group for group in groups):
            return True
    return False


def _distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Haversine distance in kilometres."""
    import math

    lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return EARTH_KM_PER_RADIAN * 2 * math.asin(math.sqrt(a))


async def all_materials(db) -> List[str]:
    """Return the distinct accepted material strings for filter chips."""
    return await db["recyclers"].distinct("accepted_materials")


async def all_types(db) -> List[str]:
    """Return the distinct facility types for filter chips."""
    return await db["recyclers"].distinct("type")


async def all_districts(db) -> List[str]:
    """Return Tamil Nadu districts represented in the directory."""
    districts = await db["recyclers"].distinct("district")
    return sorted(district for district in districts if district)
