"""Patient intake API routes for nurse onboarding workflow."""

from datetime import date, datetime
from typing import Optional

import bcrypt
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.core.response_models import SuccessResponse
from app.database.connection import get_db
from app.database.models.care_navigation_episode import (
    CareNavigationEpisode,
    EpisodeStatus,
    EpisodeType,
    TriggerType,
)
from app.database.models.organization import Organization, OrganizationStatus
from app.database.models.patient_enrollment import EnrollmentProgram, EnrollmentStatus, PatientEnrollment
from app.database.models.patient_profile import ContactMethod, Gender, PatientProfile, RiskTier
from app.database.models.role import Role, RoleName
from app.database.models.staff_profile import StaffProfile
from app.database.models.user import User, UserStatus


router = APIRouter(prefix="/patient-intake", tags=["Patient Intake"])


ENROLLMENT_PROGRAM_OPTIONS = [item.value for item in EnrollmentProgram]
ENROLLMENT_STATUS_OPTIONS = [item.value for item in EnrollmentStatus]
EPISODE_TYPE_OPTIONS = [item.value for item in EpisodeType]
TRIGGER_TYPE_OPTIONS = [item.value for item in TriggerType]
EPISODE_STATUS_OPTIONS = [item.value for item in EpisodeStatus]


class PatientOnboardFromFhirRequest(BaseModel):
    fhir_patient_id: str
    organization_id: int
    enrollment_program: str
    enrollment_status: str
    enrollment_date: Optional[datetime] = None
    created_by_user_id: Optional[int] = None

    episode_type: str
    trigger_type: str
    trigger_reference: Optional[str] = None
    episode_status: str
    opened_at: Optional[datetime] = None
    owner_staff_id: Optional[int] = None

    first_name: str
    last_name: str
    email: Optional[str] = None
    date_of_birth: date
    gender: str = "UNKNOWN"
    phone: Optional[str] = None
    preferred_language: Optional[str] = "en-US"
    preferred_contact_method: str = "SMS"
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    risk_tier: str = "UNKNOWN"
    initial_password: str = "Test@1234"


@router.get("/metadata", response_model=SuccessResponse)
async def get_patient_intake_metadata(db: Session = Depends(get_db)):
    organizations = (
        db.query(Organization)
        .filter(Organization.status == OrganizationStatus.ACTIVE)
        .order_by(Organization.organization_name.asc())
        .all()
    )

    staff_rows = (
        db.query(StaffProfile, User)
        .join(User, User.user_id == StaffProfile.user_id)
        .filter(User.status == UserStatus.ACTIVE)
        .order_by(User.first_name.asc(), User.last_name.asc())
        .all()
    )

    return SuccessResponse(
        status="success",
        message="Patient intake metadata retrieved successfully",
        data={
            "enrollment_programs": ENROLLMENT_PROGRAM_OPTIONS,
            "enrollment_statuses": ENROLLMENT_STATUS_OPTIONS,
            "episode_types": EPISODE_TYPE_OPTIONS,
            "trigger_types": TRIGGER_TYPE_OPTIONS,
            "episode_statuses": EPISODE_STATUS_OPTIONS,
            "genders": [item.value for item in Gender],
            "contact_methods": [item.value for item in ContactMethod],
            "risk_tiers": [item.value for item in RiskTier],
            "organizations": [
                {
                    "organization_id": row.organization_id,
                    "organization_name": row.organization_name,
                }
                for row in organizations
            ],
            "owner_staff": [
                {
                    "staff_id": staff.staff_id,
                    "display_name": f"{user.first_name} {user.last_name}",
                    "user_id": user.user_id,
                }
                for staff, user in staff_rows
            ],
        },
    )


@router.post("/from-fhir", response_model=SuccessResponse)
async def create_patient_from_fhir(payload: PatientOnboardFromFhirRequest, db: Session = Depends(get_db)):
    patient_profile = (
        db.query(PatientProfile)
        .filter(PatientProfile.external_fhir_patient_id == payload.fhir_patient_id)
        .first()
    )

    if patient_profile:
        existing_user = db.query(User).filter(User.user_id == patient_profile.user_id).first()
        if existing_user and existing_user.status == UserStatus.ACTIVE:
            return SuccessResponse(
                status="success",
                message="User already exists and is active",
                data={
                    "existing_user": True,
                    "user_id": existing_user.user_id,
                    "patient_id": patient_profile.patient_id,
                    "email": existing_user.email,
                    "status": existing_user.status.value,
                },
            )

        raise ConflictException(
            "User already exists for this patient but is not active",
            "USER_EXISTS_NOT_ACTIVE",
        )

    if payload.email:
        user_by_email = db.query(User).filter(User.email == payload.email).first()
        if user_by_email and user_by_email.status == UserStatus.ACTIVE:
            return SuccessResponse(
                status="success",
                message="User already exists and is active",
                data={
                    "existing_user": True,
                    "user_id": user_by_email.user_id,
                    "patient_id": None,
                    "email": user_by_email.email,
                    "status": user_by_email.status.value,
                },
            )

        if user_by_email:
            raise ConflictException(
                "User with this email exists but is not active",
                "USER_EXISTS_NOT_ACTIVE",
            )

    organization = db.query(Organization).filter(Organization.organization_id == payload.organization_id).first()
    if not organization:
        raise NotFoundException("Organization not found", "ORG_NOT_FOUND")

    patient_role = db.query(Role).filter(Role.role_name == RoleName.PATIENT).first()
    if not patient_role:
        raise NotFoundException("PATIENT role is not configured", "ROLE_NOT_FOUND")

    if payload.enrollment_program not in ENROLLMENT_PROGRAM_OPTIONS:
        raise ValidationException("Invalid enrollment_program", "INVALID_ENROLLMENT_PROGRAM")

    if payload.enrollment_status not in ENROLLMENT_STATUS_OPTIONS:
        raise ValidationException("Invalid enrollment_status", "INVALID_ENROLLMENT_STATUS")

    if payload.episode_type not in EPISODE_TYPE_OPTIONS:
        raise ValidationException("Invalid episode_type", "INVALID_EPISODE_TYPE")

    if payload.trigger_type not in TRIGGER_TYPE_OPTIONS:
        raise ValidationException("Invalid trigger_type", "INVALID_TRIGGER_TYPE")

    if payload.episode_status not in EPISODE_STATUS_OPTIONS:
        raise ValidationException("Invalid episode_status", "INVALID_EPISODE_STATUS")

    enrollment_program = EnrollmentProgram(payload.enrollment_program)
    enrollment_status = EnrollmentStatus(payload.enrollment_status)
    episode_type = EpisodeType(payload.episode_type)
    trigger_type = TriggerType(payload.trigger_type)
    episode_status = EpisodeStatus(payload.episode_status)

    try:
        gender = Gender(payload.gender)
        preferred_contact_method = ContactMethod(payload.preferred_contact_method)
        risk_tier = RiskTier(payload.risk_tier)
    except ValueError as exc:
        raise ValidationException("Invalid enum value in demographic fields", "INVALID_DEMOGRAPHICS_ENUM") from exc

    if payload.owner_staff_id is not None:
        owner_staff = db.query(StaffProfile).filter(StaffProfile.staff_id == payload.owner_staff_id).first()
        if not owner_staff:
            raise ValidationException("owner_staff_id not found", "OWNER_STAFF_NOT_FOUND")

    user_email = payload.email or f"fhir.{payload.fhir_patient_id}@patientai.local"
    password_hash = bcrypt.hashpw(payload.initial_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    try:
        user = User(
            organization_id=payload.organization_id,
            role_id=patient_role.role_id,
            first_name=payload.first_name,
            last_name=payload.last_name,
            email=user_email,
            password_hash=password_hash,
            phone=payload.phone,
            status=UserStatus.ACTIVE,
            is_verified=True,
        )

        profile = PatientProfile(
            user_id=user.user_id,
            external_fhir_patient_id=payload.fhir_patient_id,
            date_of_birth=payload.date_of_birth,
            gender=gender,
            preferred_language=payload.preferred_language or "en-US",
            preferred_contact_method=preferred_contact_method,
            emergency_contact_name=payload.emergency_contact_name,
            emergency_contact_phone=payload.emergency_contact_phone,
            risk_tier=risk_tier,
        )

        db.add(user)
        db.flush()

        profile.user_id = user.user_id
        db.add(profile)
        db.flush()

        enrollment = PatientEnrollment(
            patient_id=profile.patient_id,
            organization_id=payload.organization_id,
            enrollment_program=enrollment_program,
            enrollment_status=enrollment_status,
            enrollment_date=payload.enrollment_date or datetime.utcnow(),
            created_by_user_id=payload.created_by_user_id,
        )
        db.add(enrollment)
        db.flush()

        episode = CareNavigationEpisode(
            patient_id=profile.patient_id,
            enrollment_id=enrollment.enrollment_id,
            episode_type=episode_type,
            trigger_type=trigger_type,
            trigger_reference=payload.trigger_reference,
            status=episode_status,
            opened_at=payload.opened_at or datetime.utcnow(),
            owner_staff_id=payload.owner_staff_id,
        )
        db.add(episode)
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(user)
    db.refresh(profile)
    db.refresh(enrollment)
    db.refresh(episode)

    return SuccessResponse(
        status="success",
        message="Patient intake record created successfully",
        data={
            "existing_user": False,
            "user_id": user.user_id,
            "patient_id": profile.patient_id,
            "enrollment_id": enrollment.enrollment_id,
            "episode_id": episode.episode_id,
            "email": user.email,
            "status": user.status.value,
        },
    )
