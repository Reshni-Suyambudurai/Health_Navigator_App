"""Clinical-governance dashboard routes."""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.response_models import SuccessResponse
from app.database.connection import get_db
from app.services.navigator.clinical_governance_dashboard_service import (
    ClinicalGovernanceDashboardService,
)


router = APIRouter(prefix="/clinical-governance/dashboard", tags=["Clinical Governance Dashboard"])


@router.get("/users/{user_id}/analytics", response_model=SuccessResponse)
async def get_analytics(
    user_id: int,
    period: str = Query(default="today"),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
):
    data = ClinicalGovernanceDashboardService(db).get_analytics(
        user_id,
        period,
        start_date,
        end_date,
    )
    return SuccessResponse(
        status="success",
        message="Clinical governance analytics retrieved successfully",
        data=data,
    )