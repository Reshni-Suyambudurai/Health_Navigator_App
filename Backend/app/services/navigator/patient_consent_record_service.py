"""Business logic for patient consent operations."""

from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.database.models.patient_consent_record import PatientConsentRecord
from app.database.repositories.navigator.patient_consent_record_repository import PatientConsentRecordRepository
from app.database.repositories.navigator.patient_profile_repository import PatientProfileRepository


class PatientConsentRecordService:
    def __init__(self, db: Session):
        self.repository = PatientConsentRecordRepository(db)
        self.profile_repository = PatientProfileRepository(db)

    def create_consent(
        self,
        patient_id: int,
        consent_type: str,
        consent_text_version: str,
        captured_channel: str,
        captured_by_user_id: Optional[int] = None,
        effective_at: Optional[datetime] = None,
    ) -> PatientConsentRecord:
        if not self.profile_repository.find_by_id(patient_id):
            raise ValidationException("Patient profile does not exist", "PATIENT_PROFILE_NOT_FOUND")

        if self.repository.find_active_by_patient_and_type(patient_id, consent_type):
            raise ConflictException("Active consent already exists for this type", "CONSENT_ALREADY_ACTIVE")

        consent = PatientConsentRecord(
            patient_id=patient_id,
            consent_type=consent_type,
            consent_status="ACTIVE",
            consent_text_version=consent_text_version,
            effective_at=effective_at or datetime.utcnow(),
            captured_channel=captured_channel,
            captured_by_user_id=captured_by_user_id,
        )
        return self.repository.save(consent)

    def get_by_id(self, consent_id: int) -> PatientConsentRecord:
        consent = self.repository.find_by_id(consent_id)
        if not consent:
            raise NotFoundException("Consent record not found", "CONSENT_NOT_FOUND")
        return consent

    def list_by_patient(self, patient_id: int) -> List[PatientConsentRecord]:
        return self.repository.find_by_patient_id(patient_id)

    def revoke(self, consent_id: int) -> PatientConsentRecord:
        consent = self.get_by_id(consent_id)
        if consent.revoked_at is not None:
            raise ConflictException("Consent already revoked", "CONSENT_ALREADY_REVOKED")
        consent.consent_status = "REVOKED"
        consent.revoked_at = datetime.utcnow()
        return self.repository.save(consent)
