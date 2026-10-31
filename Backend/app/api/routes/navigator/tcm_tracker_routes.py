"""Campaign-based TCM tracker routes."""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.response_models import SuccessResponse
from app.database.connection import get_db, get_optional_monster_db
from app.services.navigator.tcm_tracker_service import TcmTrackerService


router = APIRouter(prefix="/tcm-tracker", tags=["TCM Tracker"])


@router.get("/users/{user_id}/campaigns", response_model=SuccessResponse)
async def list_campaigns(
    user_id: int,
    db: Session = Depends(get_db),
    fhir_db: Session | None = Depends(get_optional_monster_db),
):
    data = TcmTrackerService(db, fhir_db).list_campaigns(user_id)
    return SuccessResponse(
        status="success",
        message="TCM tracker campaigns retrieved successfully",
        data=data,
    )


@router.get("/users/{user_id}/summary", response_model=SuccessResponse)
async def get_summary(
    user_id: int,
    campaign_id: int | None = Query(default=None, gt=0),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    fhir_db: Session | None = Depends(get_optional_monster_db),
):
    data = TcmTrackerService(db, fhir_db).get_summary(user_id, campaign_id, from_date, to_date)
    return SuccessResponse(
        status="success",
        message="TCM tracker summary retrieved successfully",
        data=data,
    )


@router.get("/users/{user_id}/workflow-progress", response_model=SuccessResponse)
async def get_workflow_progress(
    user_id: int,
    campaign_id: int | None = Query(default=None, gt=0),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    fhir_db: Session | None = Depends(get_optional_monster_db),
):
    data = TcmTrackerService(db, fhir_db).get_workflow_progress(user_id, campaign_id, from_date, to_date)
    return SuccessResponse(
        status="success",
        message="TCM workflow progress retrieved successfully",
        data=data,
    )


@router.get("/users/{user_id}/patients", response_model=SuccessResponse)
async def list_patients(
    user_id: int,
    category: str = Query(default="ACTIVE"),
    campaign_id: int | None = Query(default=None, gt=0),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    search: str | None = Query(default=None, max_length=100),
    db: Session = Depends(get_db),
    fhir_db: Session | None = Depends(get_optional_monster_db),
):
    data = TcmTrackerService(db, fhir_db).list_patients(
        user_id,
        category,
        campaign_id,
        page,
        page_size,
        from_date,
        to_date,
        search,
    )
    return SuccessResponse(
        status="success",
        message="TCM tracker patients retrieved successfully",
        data=data,
    )


@router.get(
    "/users/{user_id}/campaigns/{campaign_id}/episodes/{episode_id}/details",
    response_model=SuccessResponse,
)
async def get_patient_details(
    user_id: int,
    campaign_id: int,
    episode_id: int,
    db: Session = Depends(get_db),
    fhir_db: Session | None = Depends(get_optional_monster_db),
):
    data = TcmTrackerService(db, fhir_db).get_patient_details(user_id, campaign_id, episode_id)
    return SuccessResponse(
        status="success",
        message="TCM patient details retrieved successfully",
        data=data,
    )