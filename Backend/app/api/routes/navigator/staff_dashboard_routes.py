"""Pharmacist and social-worker dashboard routes."""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.response_models import SuccessResponse
from app.database.connection import get_db
from app.services.navigator.staff_dashboard_service import StaffDashboardService


router = APIRouter(prefix="/staff-dashboard", tags=["Staff Dashboard"])


@router.get("/users/{user_id}/analytics", response_model=SuccessResponse)
async def get_staff_analytics(
    user_id: int,
    period: str = Query(default="TODAY"),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
):
    data = StaffDashboardService(db).get_analytics(user_id, period, from_date, to_date)
    return SuccessResponse(
        status="success",
        message="Staff dashboard analytics retrieved successfully",
        data=data,
    )
