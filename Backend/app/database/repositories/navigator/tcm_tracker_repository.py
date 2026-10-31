"""Database access for the campaign-based TCM tracker."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.models.appointment import Appointment
from app.database.models.care_navigation_episode import CareNavigationEpisode, EpisodeStatus, EpisodeType, TriggerType
from app.database.models.checkin_escalation import CheckinEscalation
from app.database.models.checkin_session import CheckinSession
from app.database.models.checkin_template import CheckinTemplate
from app.database.models.escalation_assignment import EscalationAssignment
from app.database.models.outreach_campaign import CampaignStatus, OutreachCampaign
from app.database.models.outreach_event import OutreachEvent
from app.database.models.outreach_workflow import OutreachWorkflow
from app.database.models.patient_consent_record import PatientConsentRecord
from app.database.models.patient_enrollment import EnrollmentProgram, EnrollmentStatus, PatientEnrollment
from app.database.models.patient_profile import PatientProfile
from app.database.models.role import Role, RoleName
from app.database.models.staff_profile import StaffProfile
from app.database.models.user import User, UserStatus


class TcmTrackerRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_context(self, user_id: int):
        return (
            self.db.query(User, StaffProfile, Role)
            .join(StaffProfile, StaffProfile.user_id == User.user_id)
            .join(Role, Role.role_id == User.role_id)
            .filter(User.user_id == user_id)
            .first()
        )

    def list_campaigns(self, organization_id: int):
        return (
            self.db.query(OutreachCampaign)
            .filter(
                OutreachCampaign.organization_id == organization_id,
                OutreachCampaign.status == CampaignStatus.ACTIVE,
                self.db.query(OutreachWorkflow.workflow_id)
                .filter(
                    OutreachWorkflow.campaign_id == OutreachCampaign.campaign_id,
                    OutreachWorkflow.is_active.is_(True),
                )
                .exists(),
            )
            .order_by(OutreachCampaign.campaign_name.asc())
            .all()
        )

    def list_workflows(self, campaign_ids: list[int]):
        if not campaign_ids:
            return []
        return (
            self.db.query(OutreachWorkflow, CheckinTemplate)
            .outerjoin(
                CheckinTemplate,
                CheckinTemplate.checkin_template_id == OutreachWorkflow.checkin_template_id,
            )
            .filter(
                OutreachWorkflow.campaign_id.in_(campaign_ids),
                OutreachWorkflow.is_active.is_(True),
            )
            .order_by(OutreachWorkflow.campaign_id.asc(), OutreachWorkflow.step_order.asc())
            .all()
        )

    def list_eligible_episodes(
        self,
        campaign: OutreachCampaign,
        owner_staff_id: int | None,
        from_date: datetime | None,
        to_date: datetime | None,
    ):
        accepted_consents = (
            self.db.query(PatientConsentRecord.patient_id.label("patient_id"))
            .filter(
                PatientConsentRecord.consent_type.in_(("AI_DISCLOSURE", "AI_INTERACTION")),
                PatientConsentRecord.consent_status == "ACCEPTED",
            )
            .group_by(PatientConsentRecord.patient_id)
            .having(func.count(func.distinct(PatientConsentRecord.consent_type)) == 2)
            .subquery()
        )
        query = (
            self.db.query(
                CareNavigationEpisode.episode_id.label("episode_id"),
                CareNavigationEpisode.patient_id.label("patient_id"),
                CareNavigationEpisode.status.label("episode_status"),
                CareNavigationEpisode.trigger_type.label("trigger_type"),
                CareNavigationEpisode.opened_at.label("opened_at"),
                CareNavigationEpisode.closed_at.label("closed_at"),
                CareNavigationEpisode.owner_staff_id.label("owner_staff_id"),
                PatientEnrollment.enrollment_status.label("enrollment_status"),
                PatientProfile.external_fhir_patient_id.label("external_fhir_patient_id"),
                User.first_name.label("first_name"),
                User.last_name.label("last_name"),
            )
            .join(PatientEnrollment, PatientEnrollment.enrollment_id == CareNavigationEpisode.enrollment_id)
            .join(PatientProfile, PatientProfile.patient_id == CareNavigationEpisode.patient_id)
            .join(User, User.user_id == PatientProfile.user_id)
            .join(Role, Role.role_id == User.role_id)
            .join(accepted_consents, accepted_consents.c.patient_id == PatientProfile.patient_id)
            .filter(
                PatientEnrollment.organization_id == campaign.organization_id,
                User.organization_id == campaign.organization_id,
                User.status == UserStatus.ACTIVE,
                Role.role_name == RoleName.PATIENT,
            )
        )
        criteria = campaign.target_cohort_definition or {}
        enum_filters = (
            (criteria.get("enrollment_statuses"), EnrollmentStatus, PatientEnrollment.enrollment_status),
            (criteria.get("enrollment_programs"), EnrollmentProgram, PatientEnrollment.enrollment_program),
            (criteria.get("episode_types"), EpisodeType, CareNavigationEpisode.episode_type),
            (criteria.get("episode_statuses"), EpisodeStatus, CareNavigationEpisode.status),
        )
        for values, enum_type, column in enum_filters:
            if values:
                query = query.filter(column.in_([enum_type(value) for value in values]))
        discharged_within_days = criteria.get("discharged_within_days")
        if discharged_within_days:
            query = query.filter(
                CareNavigationEpisode.trigger_type == TriggerType.DISCHARGE,
                CareNavigationEpisode.opened_at >= datetime.now(UTC).replace(tzinfo=None) - timedelta(days=discharged_within_days),
            )
        if owner_staff_id is not None:
            query = query.filter(CareNavigationEpisode.owner_staff_id == owner_staff_id)
        if from_date is not None:
            query = query.filter(CareNavigationEpisode.opened_at >= from_date)
        if to_date is not None:
            query = query.filter(CareNavigationEpisode.opened_at < to_date)
        return query.order_by(CareNavigationEpisode.opened_at.desc()).all()

    def list_events(self, campaign_ids: list[int], episode_ids: list[int]):
        if not campaign_ids or not episode_ids:
            return []
        return (
            self.db.query(OutreachEvent)
            .filter(
                OutreachEvent.campaign_id.in_(campaign_ids),
                OutreachEvent.episode_id.in_(episode_ids),
            )
            .all()
        )

    def list_sessions(self, event_ids: list[int]):
        if not event_ids:
            return []
        return self.db.query(CheckinSession).filter(CheckinSession.outreach_event_id.in_(event_ids)).all()

    def list_appointments(self, episode_ids: list[int]):
        if not episode_ids:
            return []
        return self.db.query(Appointment).filter(Appointment.episode_id.in_(episode_ids)).all()

    def list_escalations(self, session_ids: list[int]):
        if not session_ids:
            return []
        return (
            self.db.query(CheckinEscalation, EscalationAssignment, StaffProfile, User)
            .outerjoin(
                EscalationAssignment,
                EscalationAssignment.checkin_escalation_id == CheckinEscalation.checkin_escalation_id,
            )
            .outerjoin(StaffProfile, StaffProfile.staff_id == EscalationAssignment.assigned_to_staff_id)
            .outerjoin(User, User.user_id == StaffProfile.user_id)
            .filter(CheckinEscalation.checkin_session_id.in_(session_ids))
            .all()
        )