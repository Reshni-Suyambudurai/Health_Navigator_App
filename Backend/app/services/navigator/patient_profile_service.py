"""Business logic for patient profile operations."""

from typing import List, Optional
from sqlalchemy.orm import Session
from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.database.models.patient_profile import PatientProfile, Gender, ContactMethod, RiskTier
from app.database.models.user import User
from app.database.repositories.navigator.patient_profile_repository import PatientProfileRepository
from app.database.repositories.navigator.user_repository import UserRepository


class PatientProfileService:
    def __init__(self, db: Session):
        self.repository = PatientProfileRepository(db)
        self.user_repository = UserRepository(db)

    def get_by_id(self, patient_id: int) -> PatientProfile:
        profile = self.repository.find_by_id(patient_id)
        if not profile:
            raise NotFoundException("Patient profile not found", "PATIENT_PROFILE_NOT_FOUND")
        return profile

    def list_profiles(self, skip: int = 0, limit: int = 100) -> List[PatientProfile]:
        return self.repository.find_all(skip=skip, limit=limit)

    def get_by_external_fhir_patient_id(self, fhir_patient_id: str) -> PatientProfile:
        profile = self.repository.find_by_external_fhir_patient_id(fhir_patient_id)
        if not profile:
            raise NotFoundException("Patient profile not found for FHIR patient id", "PATIENT_PROFILE_NOT_FOUND")
        return profile

    def create_profile(
        self,
        user_id: int,
        date_of_birth,
        gender: Optional[str],
        preferred_language: Optional[str],
        preferred_contact_method: Optional[str],
        emergency_contact_name: Optional[str],
        emergency_contact_phone: Optional[str],
        risk_tier: Optional[str],
        external_fhir_patient_id: Optional[str],
    ) -> PatientProfile:
        user = self.user_repository.find_by_id(user_id)
        if not user:
            raise ValidationException("User does not exist", "USER_NOT_FOUND")

        if self.repository.find_by_user_id(user_id):
            raise ConflictException("Patient profile already exists for user", "PATIENT_PROFILE_EXISTS")

        if external_fhir_patient_id and self.repository.find_by_external_fhir_patient_id(external_fhir_patient_id):
            raise ConflictException("FHIR patient id already linked", "FHIR_PATIENT_LINK_EXISTS")

        profile = PatientProfile(
            user_id=user_id,
            date_of_birth=date_of_birth,
            gender=self._parse_enum(Gender, gender, "gender") if gender else None,
            preferred_language=preferred_language or "en",
            preferred_contact_method=self._parse_enum(ContactMethod, preferred_contact_method, "preferred_contact_method") if preferred_contact_method else ContactMethod.SMS,
            emergency_contact_name=emergency_contact_name,
            emergency_contact_phone=emergency_contact_phone,
            risk_tier=self._parse_enum(RiskTier, risk_tier, "risk_tier") if risk_tier else RiskTier.UNKNOWN,
            external_fhir_patient_id=external_fhir_patient_id,
        )
        return self.repository.save(profile)

    @staticmethod
    def _parse_enum(enum_cls, value: str, field: str):
        try:
            return enum_cls[value.upper()]
        except KeyError as exc:
            raise ValidationException(f"Invalid {field}: {value}", "VALIDATION_ERROR") from exc
