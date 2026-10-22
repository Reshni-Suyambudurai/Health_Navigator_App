"""Business logic for patient enrollment operations."""

from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.database.models.patient_enrollment import PatientEnrollment
from app.database.models.care_navigation_episode import EpisodeStatus, EpisodeType, TriggerType
from app.database.models.patient_profile import RiskTier
from app.database.repositories.navigator.patient_enrollment_repository import PatientEnrollmentRepository
from app.database.repositories.navigator.patient_profile_repository import PatientProfileRepository


class PatientEnrollmentService:
    def __init__(self, db: Session):
        self.repository = PatientEnrollmentRepository(db)
        self.profile_repository = PatientProfileRepository(db)

    def create_enrollment(
        self,
        patient_id: int,
        organization_id: int,
        enrollment_program: str,
        created_by_user_id: Optional[int],
        enrollment_date: Optional[datetime] = None,
    ) -> PatientEnrollment:
        if not self.profile_repository.find_by_id(patient_id):
            raise ValidationException("Patient profile does not exist", "PATIENT_PROFILE_NOT_FOUND")

        existing = self.repository.find_active_by_patient_and_program(patient_id, enrollment_program)
        if existing:
            raise ConflictException("Patient already has an active enrollment for this program", "ENROLLMENT_CONFLICT")

        enrollment = PatientEnrollment(
            patient_id=patient_id,
            organization_id=organization_id,
            enrollment_program=enrollment_program,
            enrollment_status="ACTIVE",
            enrollment_date=enrollment_date or datetime.utcnow(),
            created_by_user_id=created_by_user_id,
        )
        return self.repository.save(enrollment)

    def get_by_id(self, enrollment_id: int) -> PatientEnrollment:
        enrollment = self.repository.find_by_id(enrollment_id)
        if not enrollment:
            raise NotFoundException("Enrollment not found", "ENROLLMENT_NOT_FOUND")
        return enrollment

    def list_enrollments(
        self,
        organization_id: Optional[int],
        status: Optional[str],
        skip: int,
        limit: int,
    ) -> List[PatientEnrollment]:
        return self.repository.find_all(organization_id=organization_id, status=status, skip=skip, limit=limit)

    def list_enrollments_with_details(
        self,
        patient_id: Optional[int],
        organization_id: Optional[int],
        status: Optional[str],
        skip: int,
        limit: int,
    ):
        return self.repository.find_all_with_details(
            patient_id=patient_id,
            organization_id=organization_id,
            status=status,
            skip=skip,
            limit=limit,
        )

    def list_by_patient(self, patient_id: int) -> List[PatientEnrollment]:
        return self.repository.find_by_patient_id(patient_id)

    def get_care_details(self, patient_id: int):
        profile = self.profile_repository.find_by_id(patient_id)
        if not profile:
            raise NotFoundException("Patient profile not found", "PATIENT_PROFILE_NOT_FOUND")
        enrollment, episode = self.repository.find_latest_care_details(patient_id)
        return profile, enrollment, episode

    def get_staff_options(self):
        return [
            {
                "staff_id": staff.staff_id,
                "display_name": f"{user.first_name} {user.last_name}".strip(),
                "user_id": user.user_id,
            }
            for staff, user in self.repository.find_active_staff()
        ]

    def upsert_care_details(
        self,
        patient_id: int,
        organization_id: Optional[int],
        risk_tier: Optional[str],
        owner_staff_id: Optional[int],
        enrollment_program: str,
        enrollment_status: str,
        enrollment_date: Optional[datetime],
        close_date: Optional[datetime],
        closed_reason: Optional[str],
        episode_type: str,
        trigger_type: str,
        episode_status: str,
        opened_at: Optional[datetime],
        closed_at: Optional[datetime],
    ):
        profile = self.profile_repository.find_by_id(patient_id)
        if not profile:
            raise NotFoundException("Patient profile not found", "PATIENT_PROFILE_NOT_FOUND")

        current_enrollment, current_episode = self.repository.find_latest_care_details(patient_id)
        resolved_organization_id = organization_id or (
            profile.user.organization_id if profile.user else None
        )
        if not resolved_organization_id:
            raise ValidationException("Organization is required for patient care details", "ORGANIZATION_REQUIRED")

        if owner_staff_id is not None and not self.repository.find_active_staff_by_id(owner_staff_id):
            raise ValidationException("Owner staff member was not found", "OWNER_STAFF_NOT_FOUND")

        try:
            parsed_risk_tier = RiskTier(risk_tier) if risk_tier else profile.risk_tier
            parsed_enrollment_program = self._enum_value(enrollment_program, "enrollment_program")
            parsed_enrollment_status = self._enum_value(enrollment_status, "enrollment_status")
            parsed_episode_type = EpisodeType(episode_type)
            parsed_trigger_type = TriggerType(trigger_type)
            parsed_episode_status = EpisodeStatus(episode_status)
        except ValueError as exc:
            raise ValidationException("Invalid care detail enum value", "INVALID_CARE_DETAIL_ENUM") from exc

        profile.risk_tier = parsed_risk_tier
        self.profile_repository.save(profile)

        now = datetime.utcnow()
        enrollment, episode = self.repository.upsert_care_details(
            patient_id=patient_id,
            organization_id=resolved_organization_id,
            enrollment_program=parsed_enrollment_program,
            enrollment_status=parsed_enrollment_status,
            enrollment_date=enrollment_date or (current_enrollment.enrollment_date if current_enrollment else now),
            close_date=close_date,
            closed_reason=closed_reason,
            episode_type=parsed_episode_type,
            trigger_type=parsed_trigger_type,
            episode_status=parsed_episode_status,
            opened_at=opened_at or (current_episode.opened_at if current_episode else now),
            closed_at=closed_at if closed_at is not None else (current_episode.closed_at if current_episode else None),
            owner_staff_id=owner_staff_id,
        )
        return profile, enrollment, episode

    @staticmethod
    def _enum_value(value: str, field_name: str):
        from app.database.models.patient_enrollment import EnrollmentProgram, EnrollmentStatus

        enum_type = EnrollmentProgram if field_name == "enrollment_program" else EnrollmentStatus
        return enum_type(value)

    def update_status(
        self,
        enrollment_id: int,
        enrollment_status: str,
        closed_reason: Optional[str] = None,
        close_date: Optional[datetime] = None,
    ) -> PatientEnrollment:
        enrollment = self.get_by_id(enrollment_id)
        enrollment.enrollment_status = enrollment_status

        if enrollment_status.upper() in {"CLOSED", "INACTIVE"}:
            enrollment.close_date = close_date or datetime.utcnow()
            enrollment.closed_reason = closed_reason

        return self.repository.save(enrollment)
