"""Database access for portal outreach delivery."""

from datetime import datetime

from sqlalchemy.orm import Session

from app.database.models.outreach_campaign import OutreachCampaign
from app.database.models.checkin_session import CheckinSession, CheckinSessionStatus
from app.database.models.checkin_template import CheckinTemplate
from app.database.models.conversation_thread import ConversationStatus, ConversationThread
from app.database.models.outreach_event import OutreachEvent, OutreachEventStatus
from app.database.models.outreach_workflow import OutreachWorkflow
from app.database.models.patient_profile import PatientProfile
from app.database.models.user import User, UserStatus


class OutreachDeliveryRepository:
    """Persistence boundary for due outreach delivery."""

    def __init__(self, db: Session):
        self.db = db

    def list_due_events(self, now: datetime) -> list[OutreachEvent]:
        return (
            self.db.query(OutreachEvent)
            .filter(
                OutreachEvent.event_status == OutreachEventStatus.PENDING,
                OutreachEvent.scheduled_at <= now,
            )
            .order_by(OutreachEvent.scheduled_at.asc(), OutreachEvent.outreach_event_id.asc())
            .with_for_update(skip_locked=True)
            .all()
        )

    def get_workflow(self, workflow_id: int) -> OutreachWorkflow | None:
        return self.db.query(OutreachWorkflow).filter_by(workflow_id=workflow_id).one_or_none()

    def get_campaign(self, campaign_id: int) -> OutreachCampaign | None:
        return self.db.query(OutreachCampaign).filter_by(campaign_id=campaign_id).one_or_none()

    def get_patient(self, patient_id: int) -> tuple[PatientProfile, User] | None:
        return (
            self.db.query(PatientProfile, User)
            .join(User, User.user_id == PatientProfile.user_id)
            .filter(
                PatientProfile.patient_id == patient_id,
                User.status == UserStatus.ACTIVE,
            )
            .one_or_none()
        )

    def get_active_sender(self, user_id: int, organization_id: int) -> User | None:
        return (
            self.db.query(User)
            .filter(
                User.user_id == user_id,
                User.organization_id == organization_id,
                User.status == UserStatus.ACTIVE,
            )
            .one_or_none()
        )

    def get_session(self, event_id: int) -> CheckinSession | None:
        return self.db.query(CheckinSession).filter_by(outreach_event_id=event_id).one_or_none()

    def get_template(self, template_id: int) -> CheckinTemplate | None:
        return self.db.query(CheckinTemplate).filter_by(checkin_template_id=template_id).one_or_none()

    def list_expired_sessions(self, now: datetime) -> list[CheckinSession]:
        return (
            self.db.query(CheckinSession)
            .filter(
                CheckinSession.session_status.in_((
                    CheckinSessionStatus.PENDING,
                    CheckinSessionStatus.IN_PROGRESS,
                )),
                CheckinSession.expires_at.is_not(None),
                CheckinSession.expires_at <= now,
            )
            .with_for_update(skip_locked=True)
            .all()
        )

    def get_thread(self, patient_id: int, episode_id: int) -> ConversationThread | None:
        return (
            self.db.query(ConversationThread)
            .filter(
                ConversationThread.patient_id == patient_id,
                ConversationThread.episode_id == episode_id,
                ConversationThread.status == ConversationStatus.ACTIVE,
            )
            .order_by(ConversationThread.started_at.desc())
            .first()
        )

    def add(self, entity):
        self.db.add(entity)
        self.db.flush()
        return entity
