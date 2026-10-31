"""Database access for care-manager analytics."""

from sqlalchemy import String, cast, exists
from sqlalchemy.orm import Session

from app.database.models.appointment import Appointment
from app.database.models.appointment_action import AppointmentAction
from app.database.models.care_navigation_episode import CareNavigationEpisode
from app.database.models.checkin_response import CheckinResponse
from app.database.models.checkin_session import CheckinSession
from app.database.models.conversation_guardrail_hit import ConversationGuardrailHit
from app.database.models.escalation import Escalation
from app.database.models.escalation_action import EscalationAction
from app.database.models.escalation_assignment import EscalationAssignment
from app.database.models.follow_up_task import FollowUpTask
from app.database.models.outreach_campaign import OutreachCampaign
from app.database.models.outreach_event import OutreachEvent
from app.database.models.outreach_workflow import OutreachWorkflow
from app.database.models.patient_enrollment import PatientEnrollment
from app.database.models.patient_profile import PatientProfile
from app.database.models.role import Role
from app.database.models.staff_profile import StaffProfile
from app.database.models.user import User


class CareManagerDashboardRepository:
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

    def list_assigned_episodes(self, staff_id: int):
        return (
            self.db.query(CareNavigationEpisode, PatientProfile, PatientEnrollment, User)
            .join(PatientProfile, PatientProfile.patient_id == CareNavigationEpisode.patient_id)
            .join(PatientEnrollment, PatientEnrollment.enrollment_id == CareNavigationEpisode.enrollment_id)
            .join(User, User.user_id == PatientProfile.user_id)
            .filter(CareNavigationEpisode.owner_staff_id == staff_id)
            .order_by(CareNavigationEpisode.opened_at.desc())
            .all()
        )

    def list_enrollments(self, organization_id: int):
        return self.db.query(PatientEnrollment).filter(
            PatientEnrollment.organization_id == organization_id
        ).all()

    def list_episodes(self, organization_id: int):
        return (
            self.db.query(CareNavigationEpisode)
            .join(PatientEnrollment, PatientEnrollment.enrollment_id == CareNavigationEpisode.enrollment_id)
            .filter(PatientEnrollment.organization_id == organization_id)
            .all()
        )

    def list_appointments(self, organization_id: int):
        return (
            self.db.query(
                Appointment.appointment_id.label("appointment_id"),
                cast(Appointment.appointment_type, String).label("appointment_type"),
                Appointment.appointment_datetime.label("appointment_datetime"),
                cast(Appointment.status, String).label("status"),
                Appointment.location_or_channel.label("location_or_channel"),
                User.first_name.label("first_name"),
                User.last_name.label("last_name"),
            )
            .join(PatientProfile, PatientProfile.patient_id == Appointment.patient_id)
            .join(User, User.user_id == PatientProfile.user_id)
            .filter(
                exists().where(
                    PatientEnrollment.patient_id == PatientProfile.patient_id,
                    PatientEnrollment.organization_id == organization_id,
                )
            )
            .order_by(Appointment.appointment_datetime.desc())
            .all()
        )

    def list_appointment_actions(self, organization_id: int):
        return (
            self.db.query(AppointmentAction)
            .filter(
                exists().where(
                    PatientEnrollment.patient_id == AppointmentAction.patient_id,
                    PatientEnrollment.organization_id == organization_id,
                )
            )
            .all()
        )

    def list_outreach(self, organization_id: int):
        return (
            self.db.query(OutreachEvent, OutreachCampaign, OutreachWorkflow, PatientProfile, User)
            .join(OutreachCampaign, OutreachCampaign.campaign_id == OutreachEvent.campaign_id)
            .join(OutreachWorkflow, OutreachWorkflow.workflow_id == OutreachEvent.workflow_id)
            .join(PatientProfile, PatientProfile.patient_id == OutreachEvent.patient_id)
            .join(User, User.user_id == PatientProfile.user_id)
            .filter(OutreachCampaign.organization_id == organization_id)
            .order_by(OutreachEvent.scheduled_at.desc())
            .all()
        )

    def list_checkins(self, organization_id: int):
        return (
            self.db.query(
                CheckinSession.checkin_session_id.label("checkin_session_id"),
                cast(CheckinSession.session_status, String).label("session_status"),
            )
            .join(OutreachEvent, OutreachEvent.outreach_event_id == CheckinSession.outreach_event_id)
            .join(OutreachCampaign, OutreachCampaign.campaign_id == OutreachEvent.campaign_id)
            .filter(OutreachCampaign.organization_id == organization_id)
            .all()
        )

    def count_checkin_responses(self, organization_id: int) -> int:
        return (
            self.db.query(CheckinResponse)
            .join(CheckinSession, CheckinSession.checkin_session_id == CheckinResponse.checkin_session_id)
            .join(OutreachEvent, OutreachEvent.outreach_event_id == CheckinSession.outreach_event_id)
            .join(OutreachCampaign, OutreachCampaign.campaign_id == OutreachEvent.campaign_id)
            .filter(OutreachCampaign.organization_id == organization_id)
            .count()
        )

    def list_escalations(self, organization_id: int):
        return (
            self.db.query(Escalation, PatientProfile, User, ConversationGuardrailHit)
            .join(PatientProfile, PatientProfile.patient_id == Escalation.patient_id)
            .join(User, User.user_id == PatientProfile.user_id)
            .outerjoin(
                ConversationGuardrailHit,
                ConversationGuardrailHit.guardrail_hit_id == Escalation.guardrail_hit_id,
            )
            .filter(
                exists().where(
                    PatientEnrollment.patient_id == PatientProfile.patient_id,
                    PatientEnrollment.organization_id == organization_id,
                )
            )
            .order_by(Escalation.created_at.desc())
            .all()
        )

    def list_assignments(self, escalation_ids: list[int]):
        if not escalation_ids:
            return []
        return self.db.query(EscalationAssignment).filter(
            EscalationAssignment.escalation_id.in_(escalation_ids),
            EscalationAssignment.is_active.is_(True),
        ).all()

    def list_escalation_actions(self, escalation_ids: list[int]):
        if not escalation_ids:
            return []
        return self.db.query(EscalationAction).filter(
            EscalationAction.escalation_id.in_(escalation_ids)
        ).all()

    def list_follow_ups(self, staff_id: int):
        return (
            self.db.query(FollowUpTask, PatientProfile, User)
            .join(PatientProfile, PatientProfile.patient_id == FollowUpTask.patient_id)
            .join(User, User.user_id == PatientProfile.user_id)
            .filter(FollowUpTask.assigned_to_staff_id == staff_id)
            .order_by(FollowUpTask.due_at.asc().nullslast())
            .all()
        )
