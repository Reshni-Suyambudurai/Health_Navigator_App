"""Patient consent record API routes."""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.response_models import SuccessResponse
from app.database.connection import get_db
from app.services.navigator.patient_consent_record_service import PatientConsentRecordService


router = APIRouter(prefix="/patient-consents", tags=["Patient Consents"])


class PatientConsentCreateRequest(BaseModel):
    patient_id: int
    consent_type: str
    consent_text_version: str
    captured_channel: str
    captured_by_user_id: Optional[int] = None
    effective_at: Optional[datetime] = None


@router.post("/", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
async def create_patient_consent(payload: PatientConsentCreateRequest, db: Session = Depends(get_db)):
    service = PatientConsentRecordService(db)
    consent = service.create_consent(
        patient_id=payload.patient_id,
        consent_type=payload.consent_type,
        consent_text_version=payload.consent_text_version,
        captured_channel=payload.captured_channel,
        captured_by_user_id=payload.captured_by_user_id,
        effective_at=payload.effective_at,
    )
    return SuccessResponse(
        status="success",
        message="Patient consent created successfully",
        data={"consent_id": consent.consent_id},
    )


@router.get("/{consent_id}", response_model=SuccessResponse)
async def get_patient_consent(consent_id: int, db: Session = Depends(get_db)):
    service = PatientConsentRecordService(db)
    consent = service.get_by_id(consent_id)
    return SuccessResponse(
        status="success",
        message="Patient consent retrieved successfully",
        data={
            "consent_id": consent.consent_id,
            "patient_id": consent.patient_id,
            "consent_type": consent.consent_type,
            "consent_status": consent.consent_status,
            "consent_text_version": consent.consent_text_version,
            "effective_at": consent.effective_at.isoformat() if consent.effective_at else None,
            "revoked_at": consent.revoked_at.isoformat() if consent.revoked_at else None,
            "captured_channel": consent.captured_channel,
            "captured_by_user_id": consent.captured_by_user_id,
        },
    )


@router.get("/patient/{patient_id}", response_model=SuccessResponse)
async def list_patient_consents(patient_id: int, db: Session = Depends(get_db)):
    service = PatientConsentRecordService(db)
    consents = service.list_by_patient(patient_id)
    data = [
        {
            "consent_id": consent.consent_id,
            "consent_type": consent.consent_type,
            "consent_status": consent.consent_status,
            "effective_at": consent.effective_at.isoformat() if consent.effective_at else None,
            "revoked_at": consent.revoked_at.isoformat() if consent.revoked_at else None,
        }
        for consent in consents
    ]
    return SuccessResponse(
        status="success",
        message="Patient consents retrieved successfully",
        data={"consents": data, "count": len(data)},
    )


@router.patch("/{consent_id}/revoke", response_model=SuccessResponse)
async def revoke_patient_consent(consent_id: int, db: Session = Depends(get_db)):
    service = PatientConsentRecordService(db)
    consent = service.revoke(consent_id)
    return SuccessResponse(
        status="success",
        message="Patient consent revoked successfully",
        data={
            "consent_id": consent.consent_id,
            "consent_status": consent.consent_status,
            "revoked_at": consent.revoked_at.isoformat() if consent.revoked_at else None,
        },
    )
