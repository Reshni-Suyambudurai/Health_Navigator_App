"""Repository for patient enrollment persistence operations."""

from datetime import datetime
from typing import List, Optional, Tuple
from sqlalchemy import and_, func
from sqlalchemy.orm import Session
from app.database.models.care_navigation_episode import CareNavigationEpisode
from app.database.models.patient_consent_record import PatientConsentRecord
from app.database.models.care_navigation_episode import EpisodeStatus, EpisodeType, TriggerType
from app.database.models.patient_enrollment import PatientEnrollment
from app.database.models.patient_profile import PatientProfile
from app.database.models.staff_profile import StaffProfile
from app.database.models.user import User
from app.database.models.user import UserStatus


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

    def find_latest_care_details(self, patient_id: int):
        enrollment = (
            self.db.query(PatientEnrollment)
            .filter(PatientEnrollment.patient_id == patient_id)
            .order_by(PatientEnrollment.created_at.desc(), PatientEnrollment.enrollment_id.desc())
            .first()
        )
        if not enrollment:
            return None, None

        episode = (
            self.db.query(CareNavigationEpisode)
            .filter(CareNavigationEpisode.patient_id == patient_id)
            .filter(CareNavigationEpisode.enrollment_id == enrollment.enrollment_id)
            .order_by(CareNavigationEpisode.created_at.desc(), CareNavigationEpisode.episode_id.desc())
            .first()
        )
        return enrollment, episode

    def find_active_staff(self):
        return (
            self.db.query(StaffProfile, User)
            .join(User, User.user_id == StaffProfile.user_id)
            .filter(User.status == UserStatus.ACTIVE)
            .order_by(User.first_name.asc(), User.last_name.asc())
            .all()
        )

    def find_active_staff_by_id(self, staff_id: int) -> Optional[StaffProfile]:
        return (
            self.db.query(StaffProfile)
            .join(User, User.user_id == StaffProfile.user_id)
            .filter(StaffProfile.staff_id == staff_id)
            .filter(User.status == UserStatus.ACTIVE)
            .first()
        )

    def upsert_care_details(
        self,
        patient_id: int,
        organization_id: int,
        enrollment_program,
        enrollment_status,
        enrollment_date: datetime,
        close_date: Optional[datetime],
        closed_reason: Optional[str],
        episode_type: EpisodeType,
        trigger_type: TriggerType,
        episode_status: EpisodeStatus,
        opened_at: datetime,
        closed_at: Optional[datetime],
        owner_staff_id: Optional[int],
    ) -> Tuple[PatientEnrollment, CareNavigationEpisode]:
        enrollment, episode = self.find_latest_care_details(patient_id)

        if enrollment is None:
            enrollment = PatientEnrollment(
                patient_id=patient_id,
                organization_id=organization_id,
                enrollment_program=enrollment_program,
                enrollment_status=enrollment_status,
                enrollment_date=enrollment_date,
                close_date=close_date,
                closed_reason=closed_reason,
            )
            self.db.add(enrollment)
            self.db.flush()
        else:
            enrollment.organization_id = organization_id
            enrollment.enrollment_program = enrollment_program
            enrollment.enrollment_status = enrollment_status
            enrollment.enrollment_date = enrollment_date
            enrollment.close_date = close_date
            enrollment.closed_reason = closed_reason

        if episode is None:
            episode = CareNavigationEpisode(
                patient_id=patient_id,
                enrollment_id=enrollment.enrollment_id,
                episode_type=episode_type,
                trigger_type=trigger_type,
                status=episode_status,
                opened_at=opened_at,
                closed_at=closed_at,
                owner_staff_id=owner_staff_id,
            )
            self.db.add(episode)
        else:
            episode.episode_type = episode_type
            episode.trigger_type = trigger_type
            episode.status = episode_status
            episode.opened_at = opened_at
            episode.closed_at = closed_at
            episode.owner_staff_id = owner_staff_id

        self.db.commit()
        self.db.refresh(enrollment)
        self.db.refresh(episode)
        return enrollment, episode

    def find_all(self, organization_id: Optional[int] = None, status: Optional[str] = None, skip: int = 0, limit: int = 100) -> List[PatientEnrollment]:
        query = self.db.query(PatientEnrollment)
        if organization_id is not None:
            query = query.filter(PatientEnrollment.organization_id == organization_id)
        if status:
            query = query.filter(PatientEnrollment.enrollment_status == status)
        return query.order_by(PatientEnrollment.created_at.desc()).offset(skip).limit(limit).all()

    def find_all_with_details(
        self,
        patient_id: Optional[int] = None,
        organization_id: Optional[int] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ):
        latest_consent = (
            self.db.query(
                PatientConsentRecord.patient_id.label("consent_patient_id"),
                PatientConsentRecord.consent_status.label("consent_status"),
                PatientConsentRecord.effective_at.label("consent_captured_at"),
                PatientConsentRecord.captured_channel.label("captured_channel"),
                func.row_number()
                .over(
                    partition_by=PatientConsentRecord.patient_id,
                    order_by=(PatientConsentRecord.created_at.desc(), PatientConsentRecord.consent_id.desc()),
                )
                .label("consent_row_number"),
            )
            .subquery()
        )
        query = (
            self.db.query(
                PatientEnrollment,
                User.first_name,
                User.last_name,
                User.last_login_at,
                CareNavigationEpisode.episode_type,
                latest_consent.c.consent_status,
                latest_consent.c.consent_captured_at,
                latest_consent.c.captured_channel,
            )
            .join(PatientProfile, PatientProfile.patient_id == PatientEnrollment.patient_id)
            .join(User, User.user_id == PatientProfile.user_id)
            .outerjoin(
                CareNavigationEpisode,
                CareNavigationEpisode.enrollment_id == PatientEnrollment.enrollment_id,
            )
            .outerjoin(
                latest_consent,
                and_(
                    latest_consent.c.consent_patient_id == PatientEnrollment.patient_id,
                    latest_consent.c.consent_row_number == 1,
                ),
            )
        )
        if patient_id is not None:
            query = query.filter(PatientEnrollment.patient_id == patient_id)
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
