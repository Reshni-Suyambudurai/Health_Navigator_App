"""Repository for patient profile persistence operations."""

from typing import List, Optional
from sqlalchemy.orm import Session
from app.database.models.patient_profile import PatientProfile


class PatientProfileRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_by_id(self, patient_id: int) -> Optional[PatientProfile]:
        return self.db.query(PatientProfile).filter(PatientProfile.patient_id == patient_id).first()

    def find_by_user_id(self, user_id: int) -> Optional[PatientProfile]:
        return self.db.query(PatientProfile).filter(PatientProfile.user_id == user_id).first()

    def find_by_external_fhir_patient_id(self, fhir_patient_id: str) -> Optional[PatientProfile]:
        return (
            self.db.query(PatientProfile)
            .filter(PatientProfile.external_fhir_patient_id == fhir_patient_id)
            .first()
        )

    def find_all(self, skip: int = 0, limit: int = 100) -> List[PatientProfile]:
        return self.db.query(PatientProfile).offset(skip).limit(limit).all()

    def save(self, profile: PatientProfile) -> PatientProfile:
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile
