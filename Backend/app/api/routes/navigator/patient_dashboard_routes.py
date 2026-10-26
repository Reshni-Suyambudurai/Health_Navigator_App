"""Patient dashboard HTTP routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.response_models import SuccessResponse
from app.database.connection import get_db
from app.services.navigator.patient_dashboard_service import PatientDashboardService


router = APIRouter(prefix="/patient-dashboard", tags=["Patient Dashboard"])


@router.get("/users/{user_id}/care-snapshot", response_model=SuccessResponse)
async def get_care_snapshot(user_id: int, db: Session = Depends(get_db)):
    snapshot = PatientDashboardService(db).get_care_snapshot(user_id)
    return SuccessResponse(status="success", message="Patient care snapshot retrieved successfully", data=snapshot)