"""
User Repository - Data access layer for User operations
Similar to Spring Boot's UserRepository interface
"""

from sqlalchemy.orm import Session
from datetime import datetime
from sqlalchemy import and_
from typing import Optional, List
from app.database.models.user import User, UserStatus
from app.database.models.role import Role, RoleName
from app.database.models.care_navigation_episode import CareNavigationEpisode, EpisodeStatus
from app.database.models.patient_enrollment import EnrollmentStatus, PatientEnrollment
from app.database.models.patient_consent_record import CapturedChannel, ConsentStatus, ConsentType, PatientConsentRecord
from app.database.models.patient_profile import PatientProfile


class UserRepository:
    """
    Repository for User database operations
    Similar to Spring Boot's JpaRepository<User, Long>
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def find_by_id(self, user_id: int) -> Optional[User]:
        """Find user by ID (like findById in Spring)"""
        return self.db.query(User).filter(User.user_id == user_id).first()
    
    def find_by_email(self, email: str) -> Optional[User]:
        """Find user by email (like findByEmail in Spring)"""
        return self.db.query(User).filter(User.email == email).first()
    
    def find_all(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Get all users with pagination (like findAll with Pageable)"""
        return self.db.query(User).offset(skip).limit(limit).all()
    
    def find_by_organization_id(self, organization_id: int) -> List[User]:
        """Find users by organization"""
        return self.db.query(User).filter(User.organization_id == organization_id).all()
    
    def find_by_status(self, status: UserStatus) -> List[User]:
        """Find users by status"""
        return self.db.query(User).filter(User.status == status).all()

    def find_active_by_role(self, role_name: RoleName) -> List[User]:
        """Find active users assigned to a role."""
        return (
            self.db.query(User)
            .join(Role, User.role_id == Role.role_id)
            .filter(User.status == UserStatus.ACTIVE, Role.role_name == role_name)
            .order_by(User.first_name.asc(), User.last_name.asc())
            .all()
        )

    def has_active_patient_enrollment(self, user_id: int) -> bool:
        """Return whether the patient linked to a user has an ACTIVE enrollment."""
        return (
            self.db.query(PatientEnrollment.enrollment_id)
            .join(PatientProfile, PatientProfile.patient_id == PatientEnrollment.patient_id)
            .filter(PatientProfile.user_id == user_id)
            .filter(PatientEnrollment.enrollment_status == EnrollmentStatus.ACTIVE)
            .first()
            is not None
        )

    def initialize_patient_login(self, user_id: int) -> None:
        """Seed first-login consent rows and activate the patient's current episode."""
        profile = self.db.query(PatientProfile).filter(PatientProfile.user_id == user_id).first()
        if not profile:
            return

        consent_types = (ConsentType.AI_DISCLOSURE.value, ConsentType.AI_INTERACTION.value)
        existing_types = {
            consent_type
            for (consent_type,) in self.db.query(PatientConsentRecord.consent_type)
            .filter(
                PatientConsentRecord.patient_id == profile.patient_id,
                PatientConsentRecord.consent_type.in_(consent_types),
            )
            .all()
        }
        initialized = False
        now = datetime.utcnow()
        for consent_type in consent_types:
            if consent_type not in existing_types:
                self.db.add(PatientConsentRecord(
                    patient_id=profile.patient_id,
                    consent_type=consent_type,
                    consent_status=ConsentStatus.PENDING.value,
                    consent_text_version="v1.0",
                    effective_at=now,
                    captured_channel=CapturedChannel.PORTAL.value,
                    captured_by_user_id=user_id,
                ))
                initialized = True

        if initialized:
            self.db.query(CareNavigationEpisode).filter(
                CareNavigationEpisode.patient_id == profile.patient_id,
                CareNavigationEpisode.status != EpisodeStatus.CLOSED,
            ).update(
                {CareNavigationEpisode.status: EpisodeStatus.IN_PROGRESS},
                synchronize_session=False,
            )

        if initialized:
            self.db.commit()
    
    def save(self, user: User) -> User:
        """Save or update user (like save in Spring)"""
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def delete(self, user_id: int) -> bool:
        """Delete user by ID (like deleteById in Spring)"""
        user = self.find_by_id(user_id)
        if user:
            self.db.delete(user)
            self.db.commit()
            return True
        return False
    
    def exists_by_email(self, email: str) -> bool:
        """Check if user exists by email (like existsByEmail in Spring)"""
        return self.db.query(User).filter(User.email == email).count() > 0
    
    def count(self) -> int:
        """Count all users (like count in Spring)"""
        return self.db.query(User).count()
