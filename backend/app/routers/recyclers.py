"""Recycler routes: nearby search + filter metadata."""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from app.core.security import get_current_user
from app.db.mongodb import get_db
from app.models.recycler import RecyclerOut
from app.models.user import UserInDB
from app.services import recycler_service

router = APIRouter()


@router.get("/recyclers/nearby", response_model=List[RecyclerOut])
async def nearby_recyclers(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    material: Optional[str] = Query(default=None),
    facility_type: Optional[str] = Query(default=None),
    district: Optional[str] = Query(default=None, min_length=2, max_length=80),
    radius_km: float = Query(default=50.0, gt=0, le=200),
    db=Depends(get_db),
    current_user: UserInDB = Depends(get_current_user),
):
    return await recycler_service.find_nearby(
        db,
        latitude=lat,
        longitude=lng,
        material=material,
        type_filter=facility_type,
        district=district,
        radius_km=radius_km,
    )


@router.get("/recyclers/filters")
async def recycler_filters(
    db=Depends(get_db),
    current_user: UserInDB = Depends(get_current_user),
):
    return {
        "materials": await recycler_service.all_materials(db),
        "types": await recycler_service.all_types(db),
        "districts": await recycler_service.all_districts(db),
    }
