"""Care-manager analytics routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.response_models import SuccessResponse
from app.database.connection import get_db
from app.services.navigator.care_manager_dashboard_service import CareManagerDashboardService


router = APIRouter(prefix="/care-manager-dashboard", tags=["Care Manager Dashboard"])


@router.get("/users/{user_id}/analytics", response_model=SuccessResponse)
async def get_analytics(user_id: int, db: Session = Depends(get_db)):
    data = CareManagerDashboardService(db).get_analytics(user_id)
    return SuccessResponse(
        status="success",
        message="Care manager analytics retrieved successfully",
        data=data,
    )
