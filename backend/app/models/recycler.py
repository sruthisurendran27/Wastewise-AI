"""Recycler schemas: stored documents and API output shape."""

from typing import List, Optional

from pydantic import BaseModel, Field

RECYCLER_TYPES = ["Recycler", "Collection Centre", "Scrap Dealer"]


class GeoPoint(BaseModel):
    type: str = "Point"
    coordinates: List[float]  # [longitude, latitude]


class RecyclerOut(BaseModel):
    id: str
    name: str
    type: str
    latitude: float
    longitude: float
    address: str
    accepted_materials: List[str]
    services: List[str]
    district: Optional[str] = None
    contact: Optional[str] = None
    distance_km: Optional[float] = None
    source_url: Optional[str] = None


def recycler_doc_to_out(doc: dict, distance_km: Optional[float] = None) -> RecyclerOut:
    return RecyclerOut(
        id=str(doc["_id"]),
        name=doc["name"],
        type=doc["type"],
        latitude=doc["location"]["coordinates"][1],
        longitude=doc["location"]["coordinates"][0],
        address=doc["address"],
        district=doc.get("district"),
        accepted_materials=doc.get("accepted_materials", []),
        services=doc.get("services", []),
        contact=doc.get("contact"),
        distance_km=distance_km,
        source_url=doc.get("source_url"),
    )
