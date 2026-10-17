"""Patient first-login onboarding API routes."""

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.response_models import SuccessResponse
from app.database.connection import get_db
from app.services.navigator.patient_onboarding_service import PatientOnboardingService


router = APIRouter(prefix="/patient-onboarding", tags=["Patient Onboarding"])


class PatientProfileUpdateRequest(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone: str
    date_of_birth: date
    gender: str
    preferred_language: str
    preferred_contact_method: str
    emergency_contact_name: str
    emergency_contact_phone: str


class PatientConsentRequest(BaseModel):
    consent_text_version: str = "v1.0"
    ai_disclosure_accepted: bool
    reminders_accepted: bool


@router.get("/users/{user_id}", response_model=SuccessResponse)
async def get_patient_onboarding(user_id: int, db: Session = Depends(get_db)):
    state = PatientOnboardingService(db).get_state(user_id)
    return SuccessResponse(
        status="success",
        message="Patient onboarding state retrieved successfully",
        data=state,
    )


@router.put("/users/{user_id}/profile", response_model=SuccessResponse)
async def update_patient_profile(
    user_id: int,
    payload: PatientProfileUpdateRequest,
    db: Session = Depends(get_db),
):
    state = PatientOnboardingService(db).update_profile(user_id, payload.model_dump())
    return SuccessResponse(
        status="success",
        message="Patient profile updated successfully",
        data=state,
    )


@router.post("/users/{user_id}/consent", response_model=SuccessResponse)
async def record_patient_consent(
    user_id: int,
    payload: PatientConsentRequest,
    db: Session = Depends(get_db),
):
    state = PatientOnboardingService(db).record_consent(
        user_id,
        payload.consent_text_version,
        payload.ai_disclosure_accepted,
        payload.reminders_accepted,
    )
    return SuccessResponse(
        status="success",
        message="Patient AI consent recorded successfully",
        data=state,
    )
