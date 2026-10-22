"""Patient first-login profile verification and consent workflow."""

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException, ValidationException
from app.database.models.patient_consent_record import (
    CapturedChannel,
    ConsentStatus,
    ConsentType,
    PatientConsentRecord,
)
from app.database.models.patient_profile import ContactMethod, Gender, PatientProfile, RiskTier
from app.database.models.user import User


class PatientOnboardingService:
    def __init__(self, db: Session):
        self.db = db

    def get_state(self, user_id: int) -> dict[str, Any]:
        user = self._get_user(user_id)
        profile = self.db.query(PatientProfile).filter(PatientProfile.user_id == user_id).first()
        consents = []
        if profile:
            consents = (
                self.db.query(PatientConsentRecord)
                .filter(
                    PatientConsentRecord.patient_id == profile.patient_id,
                    PatientConsentRecord.consent_status == ConsentStatus.ACCEPTED.value,
                    PatientConsentRecord.revoked_at.is_(None),
                    PatientConsentRecord.consent_type.in_([
                        ConsentType.AI_DISCLOSURE.value,
                        ConsentType.AI_INTERACTION.value,
                    ]),
                )
                .all()
            )

        user_complete = all([user.first_name, user.last_name, user.email, user.phone])
        profile_complete = bool(profile and all([
            profile.date_of_birth,
            profile.gender,
            profile.preferred_language,
            profile.preferred_contact_method,
            profile.emergency_contact_name,
            profile.emergency_contact_phone,
        ]))
        consent_types = {consent.consent_type for consent in consents}
        consent_complete = {
            ConsentType.AI_DISCLOSURE.value,
            ConsentType.AI_INTERACTION.value,
        }.issubset(consent_types)

        return {
            "onboarding_required": not (user_complete and profile_complete and consent_complete),
            "user_complete": user_complete,
            "profile_complete": profile_complete,
            "consent_complete": consent_complete,
            "user": {
                "user_id": user.user_id,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "phone": user.phone,
            },
            "profile": self._profile_data(profile),
            "consents": sorted(consent_types),
            "options": {
                "genders": [item.value for item in Gender],
                "contact_methods": [item.value for item in ContactMethod],
            },
        }

    def update_profile(self, user_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        user = self._get_user(user_id)
        required_user_fields = ["first_name", "last_name", "email", "phone"]
        required_profile_fields = [
            "date_of_birth",
            "gender",
            "preferred_language",
            "preferred_contact_method",
            "emergency_contact_name",
            "emergency_contact_phone",
        ]
        missing = [field for field in required_user_fields + required_profile_fields if not str(payload.get(field, "")).strip()]
        if missing:
            raise ValidationException(
                f"Complete all required fields: {', '.join(missing)}",
                "PATIENT_ONBOARDING_FIELDS_REQUIRED",
            )

        duplicate_email = (
            self.db.query(User)
            .filter(User.email == payload["email"], User.user_id != user_id)
            .first()
        )
        if duplicate_email:
            raise ValidationException("That email address is already in use.", "USER_EMAIL_EXISTS")

        try:
            gender = Gender(payload["gender"])
            contact_method = ContactMethod(payload["preferred_contact_method"])
        except ValueError as exc:
            raise ValidationException("Select valid gender and contact method values.", "INVALID_PROFILE_ENUM") from exc

        user.first_name = payload["first_name"].strip()
        user.last_name = payload["last_name"].strip()
        user.email = payload["email"].strip()
        user.phone = payload["phone"].strip()

        profile = self.db.query(PatientProfile).filter(PatientProfile.user_id == user_id).first()
        if not profile:
            profile = PatientProfile(user_id=user_id, date_of_birth=payload["date_of_birth"])
            self.db.add(profile)
            self.db.flush()

        profile.date_of_birth = payload["date_of_birth"]
        profile.gender = gender
        profile.preferred_language = payload["preferred_language"].strip()
        profile.preferred_contact_method = contact_method
        profile.emergency_contact_name = payload["emergency_contact_name"].strip()
        profile.emergency_contact_phone = payload["emergency_contact_phone"].strip()

        self.db.commit()
        return self.get_state(user_id)

    def record_consent(
        self,
        user_id: int,
        text_version: str,
        ai_disclosure_accepted: bool,
        reminders_accepted: bool,
    ) -> dict[str, Any]:
        user = self._get_user(user_id)
        if not ai_disclosure_accepted or not reminders_accepted:
            raise ValidationException(
                "Both AI acknowledgements must be accepted to continue.",
                "PATIENT_CONSENT_REQUIRED",
            )
        profile = self.db.query(PatientProfile).filter(PatientProfile.user_id == user_id).first()
        if not profile:
            raise ValidationException("Complete your patient profile first.", "PATIENT_PROFILE_REQUIRED")

        state = self.get_state(user_id)
        if not state["user_complete"] or not state["profile_complete"]:
            raise ValidationException("Complete all required profile fields first.", "PATIENT_PROFILE_REQUIRED")

        existing_types = set(state["consents"])
        for consent_type in (ConsentType.AI_DISCLOSURE, ConsentType.AI_INTERACTION):
            if consent_type.value not in existing_types:
                pending_consent = (
                    self.db.query(PatientConsentRecord)
                    .filter(
                        PatientConsentRecord.patient_id == profile.patient_id,
                        PatientConsentRecord.consent_type == consent_type.value,
                        PatientConsentRecord.consent_status == ConsentStatus.PENDING.value,
                        PatientConsentRecord.revoked_at.is_(None),
                    )
                    .order_by(PatientConsentRecord.created_at.desc(), PatientConsentRecord.consent_id.desc())
                    .first()
                )
                if pending_consent:
                    pending_consent.consent_status = ConsentStatus.ACCEPTED.value
                    pending_consent.consent_text_version = text_version
                    pending_consent.effective_at = datetime.utcnow()
                    pending_consent.captured_by_user_id = user.user_id
                else:
                    self.db.add(PatientConsentRecord(
                        patient_id=profile.patient_id,
                        consent_type=consent_type.value,
                        consent_status=ConsentStatus.ACCEPTED.value,
                        consent_text_version=text_version,
                        effective_at=datetime.utcnow(),
                        captured_channel=CapturedChannel.PORTAL.value,
                        captured_by_user_id=user.user_id,
                    ))

        self.db.commit()
        return self.get_state(user_id)

    def _get_user(self, user_id: int) -> User:
        user = self.db.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise NotFoundException("User not found", "USER_NOT_FOUND")
        return user

    @staticmethod
    def _profile_data(profile: PatientProfile | None) -> dict[str, Any] | None:
        if not profile:
            return None
        return {
            "patient_id": profile.patient_id,
            "user_id": profile.user_id,
            "external_fhir_patient_id": profile.external_fhir_patient_id,
            "date_of_birth": profile.date_of_birth.isoformat() if profile.date_of_birth else None,
            "gender": profile.gender.value if profile.gender else None,
            "preferred_language": profile.preferred_language,
            "preferred_contact_method": profile.preferred_contact_method.value if profile.preferred_contact_method else None,
            "emergency_contact_name": profile.emergency_contact_name,
            "emergency_contact_phone": profile.emergency_contact_phone,
            "risk_tier": profile.risk_tier.value if profile.risk_tier else None,
        }
