"""Patient profile API routes."""

from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.response_models import SuccessResponse
from app.database.connection import get_db
from app.services.navigator.patient_profile_service import PatientProfileService


router = APIRouter(prefix="/patient-profiles", tags=["Patient Profiles"])


class PatientProfileCreateRequest(BaseModel):
    user_id: int
    date_of_birth: date
    gender: Optional[str] = None
    preferred_language: Optional[str] = "en"
    preferred_contact_method: Optional[str] = "SMS"
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    risk_tier: Optional[str] = "UNKNOWN"
    external_fhir_patient_id: Optional[str] = None


@router.post("/", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
async def create_patient_profile(payload: PatientProfileCreateRequest, db: Session = Depends(get_db)):
    service = PatientProfileService(db)
    profile = service.create_profile(
        user_id=payload.user_id,
        date_of_birth=payload.date_of_birth,
        gender=payload.gender,
        preferred_language=payload.preferred_language,
        preferred_contact_method=payload.preferred_contact_method,
        emergency_contact_name=payload.emergency_contact_name,
        emergency_contact_phone=payload.emergency_contact_phone,
        risk_tier=payload.risk_tier,
        external_fhir_patient_id=payload.external_fhir_patient_id,
    )
    return SuccessResponse(
        status="success",
        message="Patient profile created successfully",
        data={"patient_id": profile.patient_id},
    )


@router.get("/{patient_id}", response_model=SuccessResponse)
async def get_patient_profile(patient_id: int, db: Session = Depends(get_db)):
    service = PatientProfileService(db)
    profile = service.get_by_id(patient_id)
    return SuccessResponse(
        status="success",
        message="Patient profile retrieved successfully",
        data={
            "patient_id": profile.patient_id,
            "user_id": profile.user_id,
            "external_fhir_patient_id": profile.external_fhir_patient_id,
            "date_of_birth": str(profile.date_of_birth),
            "gender": profile.gender.value if profile.gender else None,
            "preferred_language": profile.preferred_language,
            "preferred_contact_method": profile.preferred_contact_method.value if profile.preferred_contact_method else None,
            "emergency_contact_name": profile.emergency_contact_name,
            "emergency_contact_phone": profile.emergency_contact_phone,
            "risk_tier": profile.risk_tier.value if profile.risk_tier else None,
        },
    )


@router.get("/", response_model=SuccessResponse)
async def list_patient_profiles(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    service = PatientProfileService(db)
    profiles = service.list_profiles(skip=skip, limit=limit)
    data = [
        {
            "patient_id": profile.patient_id,
            "user_id": profile.user_id,
            "external_fhir_patient_id": profile.external_fhir_patient_id,
            "date_of_birth": str(profile.date_of_birth),
            "gender": profile.gender.value if profile.gender else None,
            "risk_tier": profile.risk_tier.value if profile.risk_tier else None,
        }
        for profile in profiles
    ]
    return SuccessResponse(
        status="success",
        message="Patient profiles retrieved successfully",
        data={"profiles": data, "count": len(data)},
    )


@router.get("/by-fhir/{fhir_patient_id}", response_model=SuccessResponse)
async def get_patient_profile_by_fhir_id(fhir_patient_id: str, db: Session = Depends(get_db)):
    service = PatientProfileService(db)
    profile = service.get_by_external_fhir_patient_id(fhir_patient_id)
    return SuccessResponse(
        status="success",
        message="Patient profile retrieved successfully",
        data={
            "patient_id": profile.patient_id,
            "user_id": profile.user_id,
            "external_fhir_patient_id": profile.external_fhir_patient_id,
            "risk_tier": profile.risk_tier.value if profile.risk_tier else None,
        },
    )
