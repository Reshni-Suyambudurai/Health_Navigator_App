"""Database access for outreach, check-ins, and follow-up work."""

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.models.appointment import Appointment
from app.database.models.appointment_action import AppointmentAction
from app.database.models.checkin_question import CheckinQuestion
from app.database.models.checkin_escalation import CheckinEscalation
from app.database.models.checkin_escalation_response import CheckinEscalationResponse
from app.database.models.checkin_response import CheckinResponse
from app.database.models.checkin_session import CheckinSession
from app.database.models.checkin_template import CheckinTemplate
from app.database.models.care_navigation_episode import CareNavigationEpisode
from app.database.models.escalation_assignment import EscalationAssignment, EscalationAssignmentStatus
from app.database.models.follow_up_task import FollowUpTask
from app.database.models.organization import Organization
from app.database.models.outreach_campaign import OutreachCampaign
from app.database.models.outreach_event import OutreachEvent
from app.database.models.outreach_workflow import OutreachWorkflow
from app.database.models.role import Role
from app.database.models.patient_profile import PatientProfile
from app.database.models.staff_profile import StaffProfile
from app.database.models.user import User
from app.database.models.user import UserStatus


class OutreachRepository:
    def __init__(self, db: Session):
        self.db = db

    def organization_exists(self, organization_id: int) -> bool:
        return self.db.query(Organization.organization_id).filter_by(organization_id=organization_id).first() is not None

    def user_exists(self, user_id: int) -> bool:
        return self.db.query(User.user_id).filter_by(user_id=user_id).first() is not None

    def list_campaigns(self, organization_id: int | None = None) -> list[OutreachCampaign]:
        query = self.db.query(OutreachCampaign)
        if organization_id is not None:
            query = query.filter(OutreachCampaign.organization_id == organization_id)
        return query.order_by(OutreachCampaign.created_at.desc()).all()

    def get_campaign(self, campaign_id: int) -> OutreachCampaign | None:
        return self.db.query(OutreachCampaign).filter_by(campaign_id=campaign_id).one_or_none()

    def list_workflows(self, campaign_id: int) -> list[OutreachWorkflow]:
        return (
            self.db.query(OutreachWorkflow)
            .filter_by(campaign_id=campaign_id)
            .order_by(OutreachWorkflow.step_order)
            .all()
        )

    def get_workflow(self, workflow_id: int) -> OutreachWorkflow | None:
        return self.db.query(OutreachWorkflow).filter_by(workflow_id=workflow_id).one_or_none()

    def list_templates(self, organization_id: int | None = None) -> list[CheckinTemplate]:
        query = self.db.query(CheckinTemplate)
        if organization_id is not None:
            query = query.filter(CheckinTemplate.organization_id == organization_id)
        return query.order_by(CheckinTemplate.template_name, CheckinTemplate.version.desc()).all()

    def get_template(self, template_id: int) -> CheckinTemplate | None:
        return self.db.query(CheckinTemplate).filter_by(checkin_template_id=template_id).one_or_none()

    def list_questions(self, template_id: int) -> list[CheckinQuestion]:
        return (
            self.db.query(CheckinQuestion)
            .filter_by(checkin_template_id=template_id)
            .order_by(CheckinQuestion.display_order)
            .all()
        )

    def get_question(self, question_id: int) -> CheckinQuestion | None:
        return self.db.query(CheckinQuestion).filter_by(question_id=question_id).one_or_none()

    def list_events(
        self,
        campaign_id: int | None = None,
        patient_id: int | None = None,
        event_status: str | None = None,
    ) -> list[OutreachEvent]:
        query = self.db.query(OutreachEvent)
        if campaign_id is not None:
            query = query.filter(OutreachEvent.campaign_id == campaign_id)
        if patient_id is not None:
            query = query.filter(OutreachEvent.patient_id == patient_id)
        if event_status:
            query = query.filter(OutreachEvent.event_status == event_status)
        return query.order_by(OutreachEvent.scheduled_at.desc()).all()

    def get_event(self, event_id: int) -> OutreachEvent | None:
        return self.db.query(OutreachEvent).filter_by(outreach_event_id=event_id).one_or_none()

    def list_sessions(self, patient_id: int | None = None) -> list[CheckinSession]:
        query = self.db.query(CheckinSession)
        if patient_id is not None:
            query = query.filter(CheckinSession.patient_id == patient_id)
        return query.order_by(CheckinSession.created_at.desc()).all()

    def get_session(self, session_id: int) -> CheckinSession | None:
        return self.db.query(CheckinSession).filter_by(checkin_session_id=session_id).one_or_none()

    def lock_session(self, session_id: int) -> CheckinSession | None:
        return (
            self.db.query(CheckinSession)
            .filter_by(checkin_session_id=session_id)
            .with_for_update()
            .one_or_none()
        )

    def list_responses(self, session_id: int) -> list[CheckinResponse]:
        return (
            self.db.query(CheckinResponse)
            .filter_by(checkin_session_id=session_id)
            .order_by(CheckinResponse.answered_at)
            .all()
        )

    def get_response(self, session_id: int, question_id: int) -> CheckinResponse | None:
        return (
            self.db.query(CheckinResponse)
            .filter_by(checkin_session_id=session_id, question_id=question_id)
            .one_or_none()
        )

    def get_checkin_escalation(self, session_id: int) -> CheckinEscalation | None:
        return (
            self.db.query(CheckinEscalation)
            .filter_by(checkin_session_id=session_id)
            .one_or_none()
        )

    def get_checkin_escalation_response(
        self,
        escalation_id: int,
        response_id: int,
    ) -> CheckinEscalationResponse | None:
        return (
            self.db.query(CheckinEscalationResponse)
            .filter_by(
                checkin_escalation_id=escalation_id,
                response_id=response_id,
            )
            .one_or_none()
        )

    def list_checkin_escalation_responses(self, escalation_id: int) -> list[CheckinResponse]:
        return (
            self.db.query(CheckinResponse)
            .join(
                CheckinEscalationResponse,
                CheckinEscalationResponse.response_id == CheckinResponse.response_id,
            )
            .filter(CheckinEscalationResponse.checkin_escalation_id == escalation_id)
            .all()
        )

    def get_role(self, role_id: int) -> Role | None:
        return self.db.query(Role).filter_by(role_id=role_id).one_or_none()

    def get_episode(self, episode_id: int) -> CareNavigationEpisode | None:
        return self.db.query(CareNavigationEpisode).filter_by(episode_id=episode_id).one_or_none()

    def get_eligible_staff(self, staff_id: int, organization_id: int, role_id: int) -> StaffProfile | None:
        return (
            self.db.query(StaffProfile)
            .join(User, User.user_id == StaffProfile.user_id)
            .filter(
                StaffProfile.staff_id == staff_id,
                User.organization_id == organization_id,
                User.role_id == role_id,
                User.status == UserStatus.ACTIVE,
            )
            .one_or_none()
        )

    def find_least_loaded_staff(self, organization_id: int, role_id: int) -> StaffProfile | None:
        active_counts = (
            self.db.query(
                EscalationAssignment.assigned_to_staff_id.label("staff_id"),
                func.count(EscalationAssignment.assignment_id).label("active_count"),
            )
            .filter(
                EscalationAssignment.checkin_escalation_id.isnot(None),
                EscalationAssignment.is_active.is_(True),
                EscalationAssignment.assignment_status.in_((
                    EscalationAssignmentStatus.ASSIGNED,
                    EscalationAssignmentStatus.IN_PROGRESS,
                )),
            )
            .group_by(EscalationAssignment.assigned_to_staff_id)
            .subquery()
        )
        return (
            self.db.query(StaffProfile)
            .join(User, User.user_id == StaffProfile.user_id)
            .outerjoin(active_counts, active_counts.c.staff_id == StaffProfile.staff_id)
            .filter(
                User.organization_id == organization_id,
                User.role_id == role_id,
                User.status == UserStatus.ACTIVE,
            )
            .order_by(func.coalesce(active_counts.c.active_count, 0), StaffProfile.staff_id)
            .first()
        )

    def get_checkin_assignment(self, escalation_id: int) -> EscalationAssignment | None:
        return (
            self.db.query(EscalationAssignment)
            .filter_by(checkin_escalation_id=escalation_id)
            .one_or_none()
        )

    def get_staff_identity(self, staff_id: int):
        return (
            self.db.query(StaffProfile, User, Role)
            .join(User, User.user_id == StaffProfile.user_id)
            .join(Role, Role.role_id == User.role_id)
            .filter(StaffProfile.staff_id == staff_id)
            .one_or_none()
        )

    def get_staff_identity_by_user(self, user_id: int):
        return (
            self.db.query(StaffProfile, User, Role)
            .join(User, User.user_id == StaffProfile.user_id)
            .join(Role, Role.role_id == User.role_id)
            .filter(StaffProfile.user_id == user_id)
            .one_or_none()
        )

    def list_staff_checkin_assignments(self, staff_id: int) -> list[EscalationAssignment]:
        return (
            self.db.query(EscalationAssignment)
            .filter(
                EscalationAssignment.assigned_to_staff_id == staff_id,
                EscalationAssignment.checkin_escalation_id.isnot(None),
            )
            .order_by(EscalationAssignment.assigned_at.desc())
            .all()
        )

    def get_assignment(self, assignment_id: int) -> EscalationAssignment | None:
        return (
            self.db.query(EscalationAssignment)
            .filter_by(assignment_id=assignment_id)
            .one_or_none()
        )

    def get_checkin_escalation_by_id(self, escalation_id: int) -> CheckinEscalation | None:
        return (
            self.db.query(CheckinEscalation)
            .filter_by(checkin_escalation_id=escalation_id)
            .one_or_none()
        )

    def get_patient_identity(self, patient_id: int):
        return (
            self.db.query(PatientProfile, User)
            .join(User, User.user_id == PatientProfile.user_id)
            .filter(PatientProfile.patient_id == patient_id)
            .one_or_none()
        )

    def delete(self, entity) -> None:
        self.db.delete(entity)

    def get_appointment(self, appointment_id: int) -> Appointment | None:
        return self.db.query(Appointment).filter_by(appointment_id=appointment_id).one_or_none()

    def list_appointment_actions(self, appointment_id: int) -> list[AppointmentAction]:
        return (
            self.db.query(AppointmentAction)
            .filter_by(appointment_id=appointment_id)
            .order_by(AppointmentAction.created_at.desc())
            .all()
        )

    def list_tasks(
        self,
        assigned_to_staff_id: int | None = None,
        task_status: str | None = None,
    ) -> list[FollowUpTask]:
        query = self.db.query(FollowUpTask)
        if assigned_to_staff_id is not None:
            query = query.filter(FollowUpTask.assigned_to_staff_id == assigned_to_staff_id)
        if task_status:
            query = query.filter(FollowUpTask.status == task_status)
        return query.order_by(FollowUpTask.due_at.asc().nullslast(), FollowUpTask.created_at.desc()).all()

    def get_task(self, task_id: int) -> FollowUpTask | None:
        return self.db.query(FollowUpTask).filter_by(follow_up_task_id=task_id).one_or_none()

    def add(self, entity):
        self.db.add(entity)
        self.db.flush()
        return entity