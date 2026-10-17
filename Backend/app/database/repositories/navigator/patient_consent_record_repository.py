"""Repository for patient consent record persistence operations."""

from typing import List, Optional
from sqlalchemy.orm import Session
from app.database.models.patient_consent_record import PatientConsentRecord


class PatientConsentRecordRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_by_id(self, consent_id: int) -> Optional[PatientConsentRecord]:
        return self.db.query(PatientConsentRecord).filter(PatientConsentRecord.consent_id == consent_id).first()

    def find_by_patient_id(self, patient_id: int) -> List[PatientConsentRecord]:
        return (
            self.db.query(PatientConsentRecord)
            .filter(PatientConsentRecord.patient_id == patient_id)
            .order_by(PatientConsentRecord.created_at.desc())
            .all()
        )

    def find_active_by_patient_and_type(self, patient_id: int, consent_type: str) -> Optional[PatientConsentRecord]:
        return (
            self.db.query(PatientConsentRecord)
            .filter(PatientConsentRecord.patient_id == patient_id)
            .filter(PatientConsentRecord.consent_type == consent_type)
            .filter(PatientConsentRecord.consent_status == "ACTIVE")
            .filter(PatientConsentRecord.revoked_at.is_(None))
            .first()
        )

    def save(self, consent: PatientConsentRecord) -> PatientConsentRecord:
        self.db.add(consent)
        self.db.commit()
        self.db.refresh(consent)
        return consent
