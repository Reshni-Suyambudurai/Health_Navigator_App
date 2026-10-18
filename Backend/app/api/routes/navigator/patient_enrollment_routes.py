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
    organization_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    service = PatientEnrollmentService(db)
    enrollments = service.list_enrollments_with_details(
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
            "enrollment_program": enrollment.enrollment_program,
            "enrollment_status": enrollment.enrollment_status,
            "enrollment_date": enrollment.enrollment_date.isoformat() if enrollment.enrollment_date else None,
            "episode_type": episode_type.value if episode_type else None,
        }
        for enrollment, first_name, last_name, episode_type in enrollments
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
