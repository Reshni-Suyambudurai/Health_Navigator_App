"""Database operations for patient conversation threads and messages."""

from datetime import datetime
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.models.care_navigation_episode import CareNavigationEpisode, EpisodeStatus
from app.database.models.care_team_queue import CareTeamQueue, QueueStatus, QueueType
from app.database.models.clinical_guardrail_matcher import ClinicalGuardrailMatcher
from app.database.models.clinical_guardrail_rule import ClinicalGuardrailRule, RuleStatus
from app.database.models.conversation_guardrail_hit import ConversationGuardrailHit
from app.database.models.conversation_message import ConversationMessage
from app.database.models.conversation_thread import ConversationStatus, ConversationThread
from app.database.models.emergency_event import EmergencyEvent
from app.database.models.escalation import Escalation
from app.database.models.patient_enrollment import PatientEnrollment
from app.database.models.patient_profile import PatientProfile


class ConversationRepository:
    """Persistence boundary for patient chat threads and messages."""

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

    def find_active_thread(self, patient_id: int, episode_id: int) -> Optional[ConversationThread]:
        return (
            self.db.query(ConversationThread)
            .filter(ConversationThread.patient_id == patient_id)
            .filter(ConversationThread.episode_id == episode_id)
            .filter(ConversationThread.status == ConversationStatus.ACTIVE)
            .order_by(ConversationThread.started_at.desc())
            .first()
        )

    def find_paused_emergency_thread(self, patient_id: int, episode_id: int) -> Optional[ConversationThread]:
        return (
            self.db.query(ConversationThread)
            .filter(ConversationThread.patient_id == patient_id)
            .filter(ConversationThread.episode_id == episode_id)
            .filter(ConversationThread.status == ConversationStatus.PAUSED_EMERGENCY)
            .order_by(ConversationThread.started_at.desc())
            .first()
        )

    def find_current_thread(self, patient_id: int, episode_id: int) -> Optional[ConversationThread]:
        return (
            self.db.query(ConversationThread)
            .filter(ConversationThread.patient_id == patient_id)
            .filter(ConversationThread.episode_id == episode_id)
            .filter(ConversationThread.status.in_([ConversationStatus.ACTIVE, ConversationStatus.PAUSED_EMERGENCY]))
            .order_by(ConversationThread.started_at.desc())
            .first()
        )

    def find_thread_for_patient(self, patient_id: int, thread_id: int) -> Optional[ConversationThread]:
        return (
            self.db.query(ConversationThread)
            .filter(ConversationThread.thread_id == thread_id)
            .filter(ConversationThread.patient_id == patient_id)
            .first()
        )

    def list_thread_summaries(self, patient_id: int) -> list[tuple[ConversationThread, int]]:
        return (
            self.db.query(
                ConversationThread,
                func.count(ConversationMessage.message_id).label("message_count"),
            )
            .outerjoin(ConversationMessage, ConversationMessage.thread_id == ConversationThread.thread_id)
            .filter(ConversationThread.patient_id == patient_id)
            .group_by(ConversationThread.thread_id)
            .order_by(ConversationThread.started_at.desc(), ConversationThread.thread_id.desc())
            .all()
        )

    def pause_for_emergency(self, thread: ConversationThread) -> None:
        thread.status = ConversationStatus.PAUSED_EMERGENCY
        self.db.flush()

    def create_thread(self, thread: ConversationThread) -> ConversationThread:
        self.db.add(thread)
        self.db.flush()
        return thread

    def add_message(self, message: ConversationMessage) -> ConversationMessage:
        self.db.add(message)
        self.db.flush()
        return message

    def find_active_queue(self, enrollment_id: int, queue_type: QueueType) -> Optional[CareTeamQueue]:
        return (
            self.db.query(CareTeamQueue)
            .join(PatientEnrollment, CareTeamQueue.organization_id == PatientEnrollment.organization_id)
            .filter(PatientEnrollment.enrollment_id == enrollment_id)
            .filter(CareTeamQueue.queue_type == queue_type)
            .filter(CareTeamQueue.status == QueueStatus.ACTIVE)
            .first()
        )

    def create_escalation(self, escalation: Escalation) -> Escalation:
        self.db.add(escalation)
        self.db.flush()
        return escalation

    def list_patient_escalations(self, patient_id: int) -> list[Escalation]:
        return (
            self.db.query(Escalation)
            .filter(Escalation.patient_id == patient_id)
            .order_by(Escalation.created_at.desc())
            .all()
        )

    def list_active_guardrail_matchers(self) -> list[tuple[ClinicalGuardrailRule, ClinicalGuardrailMatcher]]:
        return (
            self.db.query(ClinicalGuardrailRule, ClinicalGuardrailMatcher)
            .join(ClinicalGuardrailMatcher, ClinicalGuardrailMatcher.rule_id == ClinicalGuardrailRule.rule_id)
            .filter(ClinicalGuardrailRule.status == RuleStatus.ACTIVE)
            .filter(ClinicalGuardrailMatcher.is_active.is_(True))
            .order_by(ClinicalGuardrailMatcher.priority.asc(), ClinicalGuardrailRule.rule_id.asc(), ClinicalGuardrailMatcher.matcher_id.asc())
            .all()
        )

    def add_guardrail_hit(self, guardrail_hit: ConversationGuardrailHit) -> ConversationGuardrailHit:
        self.db.add(guardrail_hit)
        self.db.flush()
        return guardrail_hit

    def add_emergency_event(self, emergency_event: EmergencyEvent) -> EmergencyEvent:
        self.db.add(emergency_event)
        self.db.flush()
        return emergency_event

    def list_messages(self, thread_id: int, limit: int = 50) -> list[ConversationMessage]:
        messages = (
            self.db.query(ConversationMessage)
            .filter(ConversationMessage.thread_id == thread_id)
            .order_by(ConversationMessage.sent_at.desc())
            .limit(limit)
            .all()
        )
        return list(reversed(messages))

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()

    @staticmethod
    def now() -> datetime:
        return datetime.utcnow()