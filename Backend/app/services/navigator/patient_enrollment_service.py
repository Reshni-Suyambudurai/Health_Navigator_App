"""Business logic for patient enrollment operations."""

from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.database.models.patient_enrollment import PatientEnrollment
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

    def list_by_patient(self, patient_id: int) -> List[PatientEnrollment]:
        return self.repository.find_by_patient_id(patient_id)

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
