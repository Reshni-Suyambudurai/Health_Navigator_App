"""Repository for patient enrollment persistence operations."""

from typing import List, Optional
from sqlalchemy.orm import Session
from app.database.models.patient_enrollment import PatientEnrollment


class PatientEnrollmentRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_by_id(self, enrollment_id: int) -> Optional[PatientEnrollment]:
        return self.db.query(PatientEnrollment).filter(PatientEnrollment.enrollment_id == enrollment_id).first()

    def find_by_patient_id(self, patient_id: int) -> List[PatientEnrollment]:
        return (
            self.db.query(PatientEnrollment)
            .filter(PatientEnrollment.patient_id == patient_id)
            .order_by(PatientEnrollment.created_at.desc())
            .all()
        )

    def find_all(self, organization_id: Optional[int] = None, status: Optional[str] = None, skip: int = 0, limit: int = 100) -> List[PatientEnrollment]:
        query = self.db.query(PatientEnrollment)
        if organization_id is not None:
            query = query.filter(PatientEnrollment.organization_id == organization_id)
        if status:
            query = query.filter(PatientEnrollment.enrollment_status == status)
        return query.order_by(PatientEnrollment.created_at.desc()).offset(skip).limit(limit).all()

    def find_active_by_patient_and_program(self, patient_id: int, program: str) -> Optional[PatientEnrollment]:
        return (
            self.db.query(PatientEnrollment)
            .filter(PatientEnrollment.patient_id == patient_id)
            .filter(PatientEnrollment.enrollment_program == program)
            .filter(PatientEnrollment.enrollment_status == "ACTIVE")
            .first()
        )

    def save(self, enrollment: PatientEnrollment) -> PatientEnrollment:
        self.db.add(enrollment)
        self.db.commit()
        self.db.refresh(enrollment)
        return enrollment
