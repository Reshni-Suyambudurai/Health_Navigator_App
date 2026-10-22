"""Patient enrollment API routes."""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.response_models import SuccessResponse
from app.database.connection import get_db
from app.services.navigator.patient_enrollment_service import PatientEnrollmentService


router = APIRouter(prefix="/patient-enrollments", tags=["Patient Enrollments"])


class PatientEnrollmentCreateRequest(BaseModel):
    patient_id: int
    organization_id: int
    enrollment_program: str
    created_by_user_id: Optional[int] = None
    enrollment_date: Optional[datetime] = None


class PatientEnrollmentStatusUpdateRequest(BaseModel):
    enrollment_status: str
    close_date: Optional[datetime] = None
    closed_reason: Optional[str] = None


class PatientCareDetailsUpsertRequest(BaseModel):
    organization_id: Optional[int] = None
    risk_tier: Optional[str] = None
    owner_staff_id: Optional[int] = None
    enrollment_program: str = "CARE_NAVIGATION"
    enrollment_status: str = "ACTIVE"
    enrollment_date: Optional[datetime] = None
    close_date: Optional[datetime] = None
    closed_reason: Optional[str] = None
    episode_type: str = "GENERAL_NAVIGATION"
    trigger_type: str = "MANUAL"
    episode_status: str = "OPEN"
    opened_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None


@router.post("/", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
async def create_patient_enrollment(payload: PatientEnrollmentCreateRequest, db: Session = Depends(get_db)):
    service = PatientEnrollmentService(db)
    enrollment = service.create_enrollment(
        patient_id=payload.patient_id,
        organization_id=payload.organization_id,
        enrollment_program=payload.enrollment_program,
        created_by_user_id=payload.created_by_user_id,
        enrollment_date=payload.enrollment_date,
    )
    return SuccessResponse(
        status="success",
        message="Patient enrolled successfully",
        data={"enrollment_id": enrollment.enrollment_id},
    )


def serialize_care_details(profile, enrollment, episode):
    return {
        "risk_tier": profile.risk_tier.value if profile.risk_tier else None,
        "enrollment": {
            "enrollment_id": enrollment.enrollment_id,
            "patient_id": enrollment.patient_id,
            "organization_id": enrollment.organization_id,
            "enrollment_program": enrollment.enrollment_program.value,
            "enrollment_status": enrollment.enrollment_status.value,
            "enrollment_date": enrollment.enrollment_date.isoformat() if enrollment.enrollment_date else None,
            "close_date": enrollment.close_date.isoformat() if enrollment.close_date else None,
            "closed_reason": enrollment.closed_reason,
        },
        "episode": {
            "episode_id": episode.episode_id,
            "patient_id": episode.patient_id,
            "enrollment_id": episode.enrollment_id,
            "episode_type": episode.episode_type.value,
            "trigger_type": episode.trigger_type.value,
            "episode_status": episode.status.value,
            "opened_at": episode.opened_at.isoformat() if episode.opened_at else None,
            "closed_at": episode.closed_at.isoformat() if episode.closed_at else None,
            "owner_staff_id": episode.owner_staff_id,
        } if episode else None,
    }


@router.get("/patient/{patient_id}/care-details", response_model=SuccessResponse)
async def get_patient_care_details(patient_id: int, db: Session = Depends(get_db)):
    service = PatientEnrollmentService(db)
    profile, enrollment, episode = service.get_care_details(patient_id)
    staff_options = service.get_staff_options()
    return SuccessResponse(
        status="success",
        message="Patient care details retrieved successfully",
        data=(serialize_care_details(profile, enrollment, episode) if enrollment else {
            "risk_tier": profile.risk_tier.value if profile.risk_tier else None,
            "enrollment": None,
            "episode": None,
        }) | {"owner_staff": staff_options},
    )


@router.put("/patient/{patient_id}/care-details", response_model=SuccessResponse)
async def upsert_patient_care_details(
    patient_id: int,
    payload: PatientCareDetailsUpsertRequest,
    db: Session = Depends(get_db),
):
    service = PatientEnrollmentService(db)
    profile, enrollment, episode = service.upsert_care_details(
        patient_id=patient_id,
        organization_id=payload.organization_id,
        risk_tier=payload.risk_tier,
        owner_staff_id=payload.owner_staff_id,
        enrollment_program=payload.enrollment_program,
        enrollment_status=payload.enrollment_status,
        enrollment_date=payload.enrollment_date,
        close_date=payload.close_date,
        closed_reason=payload.closed_reason,
        episode_type=payload.episode_type,
        trigger_type=payload.trigger_type,
        episode_status=payload.episode_status,
        opened_at=payload.opened_at,
        closed_at=payload.closed_at,
    )
    return SuccessResponse(
        status="success",
        message="Patient care details saved successfully",
        data=serialize_care_details(profile, enrollment, episode) | {"owner_staff": service.get_staff_options()},
    )
@router.get("/{enrollment_id}", response_model=SuccessResponse)
async def get_patient_enrollment(enrollment_id: int, db: Session = Depends(get_db)):
    service = PatientEnrollmentService(db)
    enrollment = service.get_by_id(enrollment_id)
    return SuccessResponse(
        status="success",
        message="Patient enrollment retrieved successfully",
        data={
            "enrollment_id": enrollment.enrollment_id,
            "patient_id": enrollment.patient_id,
            "organization_id": enrollment.organization_id,
            "enrollment_program": enrollment.enrollment_program,
            "enrollment_status": enrollment.enrollment_status,
            "enrollment_date": enrollment.enrollment_date.isoformat() if enrollment.enrollment_date else None,
            "close_date": enrollment.close_date.isoformat() if enrollment.close_date else None,
            "closed_reason": enrollment.closed_reason,
        },
    )


@router.get("/", response_model=SuccessResponse)
async def list_patient_enrollments(
    patient_id: Optional[int] = None,
    organization_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    service = PatientEnrollmentService(db)
    enrollments = service.list_enrollments_with_details(
        patient_id=patient_id,
        organization_id=organization_id,
        status=status_filter,
        skip=skip,
        limit=limit,
    )
    data = [
        {
            "enrollment_id": enrollment.enrollment_id,
            "patient_id": enrollment.patient_id,
            "first_name": first_name,
            "last_name": last_name,
            "organization_id": enrollment.organization_id,
            "enrollment_program": enrollment.enrollment_program.value,
            "enrollment_status": enrollment.enrollment_status.value,
            "enrollment_date": enrollment.enrollment_date.isoformat() if enrollment.enrollment_date else None,
            "last_login_at": last_login_at.isoformat() if last_login_at else None,
            "episode_type": episode_type.value if episode_type else None,
            "consent_status": consent_status,
            "consent_captured_at": consent_captured_at.isoformat() if consent_captured_at else None,
            "captured_channel": captured_channel,
        }
        for (
            enrollment,
            first_name,
            last_name,
            last_login_at,
            episode_type,
            consent_status,
            consent_captured_at,
            captured_channel,
        ) in enrollments
    ]
    return SuccessResponse(
        status="success",
        message="Patient enrollments retrieved successfully",
        data={"enrollments": data, "count": len(data)},
    )


@router.get("/patient/{patient_id}", response_model=SuccessResponse)
async def list_patient_enrollments_by_patient(patient_id: int, db: Session = Depends(get_db)):
    service = PatientEnrollmentService(db)
    enrollments = service.list_by_patient(patient_id)
    data = [
        {
            "enrollment_id": enrollment.enrollment_id,
            "enrollment_program": enrollment.enrollment_program,
            "enrollment_status": enrollment.enrollment_status,
            "enrollment_date": enrollment.enrollment_date.isoformat() if enrollment.enrollment_date else None,
            "close_date": enrollment.close_date.isoformat() if enrollment.close_date else None,
            "closed_reason": enrollment.closed_reason,
        }
        for enrollment in enrollments
    ]
    return SuccessResponse(
        status="success",
        message="Patient enrollments retrieved successfully",
        data={"enrollments": data, "count": len(data)},
    )


@router.patch("/{enrollment_id}/status", response_model=SuccessResponse)
async def update_patient_enrollment_status(
    enrollment_id: int,
    payload: PatientEnrollmentStatusUpdateRequest,
    db: Session = Depends(get_db),
):
    service = PatientEnrollmentService(db)
    enrollment = service.update_status(
        enrollment_id=enrollment_id,
        enrollment_status=payload.enrollment_status,
        close_date=payload.close_date,
        closed_reason=payload.closed_reason,
    )
    return SuccessResponse(
        status="success",
        message="Patient enrollment status updated successfully",
        data={
            "enrollment_id": enrollment.enrollment_id,
            "enrollment_status": enrollment.enrollment_status,
            "close_date": enrollment.close_date.isoformat() if enrollment.close_date else None,
            "closed_reason": enrollment.closed_reason,
        },
    )
