"""Database operations for the patient dashboard care snapshot."""

from typing import Optional

from sqlalchemy.orm import Session

from app.database.models.care_navigation_episode import CareNavigationEpisode, EpisodeStatus
from app.database.models.care_team_queue import CareTeamQueue, QueueStatus, QueueType
from app.database.models.patient_enrollment import PatientEnrollment
from app.database.models.patient_profile import PatientProfile
from app.database.models.queue_membership import QueueMembership, QueueRole
from app.database.models.staff_profile import StaffProfile
from app.database.models.user import User, UserStatus


class PatientDashboardRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_patient_by_user_id(self, user_id: int) -> Optional[PatientProfile]:
        return self.db.query(PatientProfile).filter(PatientProfile.user_id == user_id).first()

    def find_active_episode(self, patient_id: int) -> Optional[CareNavigationEpisode]:
        return (
            self.db.query(CareNavigationEpisode)
            .filter(CareNavigationEpisode.patient_id == patient_id)
            .filter(CareNavigationEpisode.status.in_([EpisodeStatus.OPEN, EpisodeStatus.IN_PROGRESS]))
            .order_by(CareNavigationEpisode.opened_at.desc())
            .first()
        )

    def find_staff_user(self, staff_id: int) -> Optional[User]:
        return (
            self.db.query(User)
            .join(StaffProfile, StaffProfile.user_id == User.user_id)
            .filter(StaffProfile.staff_id == staff_id, User.status == UserStatus.ACTIVE)
            .first()
        )

    def list_clinical_queue_users(self, enrollment_id: int) -> list[User]:
        return (
            self.db.query(User)
            .join(StaffProfile, StaffProfile.user_id == User.user_id)
            .join(QueueMembership, QueueMembership.staff_id == StaffProfile.staff_id)
            .join(CareTeamQueue, CareTeamQueue.queue_id == QueueMembership.queue_id)
            .join(PatientEnrollment, PatientEnrollment.organization_id == CareTeamQueue.organization_id)
            .filter(CareTeamQueue.queue_type == QueueType.CLINICAL)
            .filter(CareTeamQueue.status == QueueStatus.ACTIVE)
            .filter(QueueMembership.is_active.is_(True))
            .filter(User.status == UserStatus.ACTIVE)
            .filter(PatientEnrollment.enrollment_id == enrollment_id)
            .order_by((QueueMembership.role_in_queue == QueueRole.PRIMARY).desc(), User.last_name.asc(), User.first_name.asc())
            .all()
        )