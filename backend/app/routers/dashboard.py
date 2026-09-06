"""Dashboard routes: aggregated user stats plus recent activity."""

from fastapi import APIRouter, Depends, HTTPException

from app.core.security import get_current_user
from app.db.mongodb import get_db
from app.models.activity import DashboardStats
from app.models.user import UserInDB, public_user_from_doc
from app.services import points_service

router = APIRouter()


@router.get("/dashboard", response_model=DashboardStats)
async def dashboard(db=Depends(get_db), current_user: UserInDB = Depends(get_current_user)):
    try:
        return await points_service.get_dashboard_stats(db, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))