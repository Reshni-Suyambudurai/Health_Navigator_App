"""Deliver due portal check-in outreach events."""

from datetime import datetime, timedelta
import logging

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import ValidationException
from app.database.models.checkin_session import CheckinSession, CheckinSessionStatus
from app.database.models.conversation_message import ConversationMessage, SenderType
from app.database.models.conversation_thread import ConversationChannel, ConversationStatus, ConversationThread
from app.database.models.notification import Notification, NotificationPriority, NotificationStatus, NotificationType
from app.database.models.outreach_event import DeliveryStatus, OutreachEvent, OutreachEventChannel, OutreachEventStatus
from app.database.repositories.navigator.outreach_delivery_repository import OutreachDeliveryRepository
from app.services.navigator.checkin_session_expiry import calculate_session_expiry


logger = logging.getLogger(__name__)


class OutreachDeliveryService:
    """Create the patient-facing portal records for due check-in events."""

    def __init__(self, db: Session):
        self.db = db
        self.repository = OutreachDeliveryRepository(db)

    def process_due_events(self, now: datetime | None = None) -> dict[str, int]:
        evaluated_at = now or datetime.utcnow()
        result = {"scanned": 0, "delivered": 0, "failed": 0}
        for event in self.repository.list_due_events(evaluated_at):
            result["scanned"] += 1
            try:
                self._deliver_event(event, evaluated_at)
                self.db.commit()
                result["delivered"] += 1
            except (SQLAlchemyError, ValidationException) as exc:
                self.db.rollback()
                self._record_failure(event, str(exc), evaluated_at)
                result["failed"] += 1
                logger.exception("Outreach delivery failed for event %s", event.outreach_event_id)
        return result

    def expire_sessions(self, now: datetime | None = None) -> dict[str, int]:
        evaluated_at = now or datetime.utcnow()
        sessions = self.repository.list_expired_sessions(evaluated_at)
        for session in sessions:
            session.session_status = CheckinSessionStatus.EXPIRED
        self.db.commit()
        return {"scanned": len(sessions), "expired": len(sessions)}

    def _deliver_event(self, event, delivered_at: datetime) -> None:
        if event.channel != OutreachEventChannel.PORTAL:
            raise ValidationException("Only PORTAL outreach delivery is currently supported", "OUTREACH_CHANNEL_UNSUPPORTED")

        workflow = self.repository.get_workflow(event.workflow_id)
        if not workflow or not workflow.checkin_template_id:
            raise ValidationException("A check-in template is required for portal delivery", "CHECKIN_TEMPLATE_REQUIRED")
        template = self.repository.get_template(workflow.checkin_template_id)
        if not template:
            raise ValidationException("Check-in template not found", "CHECKIN_TEMPLATE_NOT_FOUND")
        campaign = self.repository.get_campaign(event.campaign_id)
        patient = self.repository.get_patient(event.patient_id)
        if not campaign or not patient or event.episode_id is None:
            raise ValidationException("The outreach event is missing delivery records", "OUTREACH_DELIVERY_DATA_MISSING")
        patient_profile, patient_user = patient
        sender = self.repository.get_active_sender(campaign.created_by_user_id, campaign.organization_id)
        if not sender or sender.user_id == patient_user.user_id:
            raise ValidationException("An active staff sender is required for portal delivery", "OUTREACH_SENDER_REQUIRED")

        session = self.repository.get_session(event.outreach_event_id)
        if session and session.session_status == CheckinSessionStatus.COMPLETED:
            event.event_status = OutreachEventStatus.COMPLETED
            event.completed_at = delivered_at
            return
        if session and session.session_status in (
            CheckinSessionStatus.EXPIRED,
            CheckinSessionStatus.ABANDONED,
            CheckinSessionStatus.ESCALATED,
        ):
            event.event_status = OutreachEventStatus.CANCELLED
            event.completed_at = delivered_at
            event.last_error = f"Check-in session is {session.session_status.value}."
            return

        attempt_number = (event.attempt_count or 0) + 1
        if attempt_number > workflow.max_attempts:
            event.event_status = OutreachEventStatus.FAILED
            event.completed_at = delivered_at
            event.last_error = "Maximum outreach attempts reached without a completed check-in."
            return

        template_name = getattr(template, "template_name", None)

        if session is None:
            thread = self.repository.get_thread(event.patient_id, event.episode_id)
            if thread is None:
                thread = self.repository.add(ConversationThread(
                    patient_id=event.patient_id,
                    episode_id=event.episode_id,
                    channel=ConversationChannel.PORTAL,
                    language=patient_profile.preferred_language or "en",
                    started_at=delivered_at,
                    status=ConversationStatus.ACTIVE,
                ))
            session = self.repository.add(CheckinSession(
                patient_id=event.patient_id,
                episode_id=event.episode_id,
                outreach_event_id=event.outreach_event_id,
                checkin_template_id=workflow.checkin_template_id,
                thread_id=thread.thread_id,
                session_status=CheckinSessionStatus.PENDING,
                scheduled_at=event.scheduled_at,
                expires_at=calculate_session_expiry(event.scheduled_at, template.expiry_after_hours),
            ))
            message_text = (
                f"{template_name}: open the Check-in section in the side panel and fill it in now."
                if template_name
                else "Open the Check-in section in the side panel and fill it in now."
            )
            self.repository.add(ConversationMessage(
                thread_id=thread.thread_id,
                sender_type=SenderType.SYSTEM,
                sender_user_id=sender.user_id,
                message_text=message_text,
                message_intent="CHECKIN_INVITATION",
                message_metadata={
                    "outreach_event_id": event.outreach_event_id,
                    "checkin_session_id": session.checkin_session_id,
                    "checkin_template_id": workflow.checkin_template_id,
                    "route": f"/patient/check-ins/{session.checkin_session_id}",
                },
                sent_at=delivered_at,
            ))
        notification_title = "Check-in reminder" if attempt_number > 1 else "Check-in required"
        notification_message = (
            f"{template_name}: open the Check-in section in the side panel and fill it in now."
            if template_name
            else "Open the Check-in section in the side panel and fill it in now."
        )
        self.repository.add(Notification(
            organization_id=campaign.organization_id,
            sender_user_id=sender.user_id,
            recipient_user_id=patient_user.user_id,
            title=notification_title,
            message=notification_message,
            notification_type=NotificationType.OUTREACH_UPDATE,
            priority=NotificationPriority.NORMAL,
            status=NotificationStatus.UNREAD,
        ))

        event.delivery_status = DeliveryStatus.SENT
        event.sent_at = delivered_at
        event.attempt_count = attempt_number
        event.last_error = None
        if attempt_number < workflow.max_attempts:
            event.event_status = OutreachEventStatus.PENDING
            event.scheduled_at = delivered_at + timedelta(minutes=workflow.retry_interval_minutes)
        else:
            event.event_status = OutreachEventStatus.FAILED
            event.completed_at = delivered_at
            event.last_error = "Maximum outreach attempts reached without a completed check-in."

    def _record_failure(self, event, error: str, failed_at: datetime) -> None:
        failed_event = self.db.query(OutreachEvent).filter_by(outreach_event_id=event.outreach_event_id).one_or_none()
        if failed_event is None:
            return
        workflow = self.repository.get_workflow(event.workflow_id)
        failed_event.delivery_status = DeliveryStatus.FAILED
        failed_event.attempt_count = (failed_event.attempt_count or 0) + 1
        failed_event.last_error = error[:2000]
        if workflow and failed_event.attempt_count < workflow.max_attempts:
            failed_event.event_status = OutreachEventStatus.PENDING
            failed_event.scheduled_at = failed_at + timedelta(minutes=workflow.retry_interval_minutes)
        else:
            failed_event.event_status = OutreachEventStatus.FAILED
            failed_event.completed_at = failed_at
        self.db.commit()
