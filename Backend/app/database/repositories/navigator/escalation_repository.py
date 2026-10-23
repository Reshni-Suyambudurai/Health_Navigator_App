"""Database operations for care-team escalation workflows."""

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.database.models.care_team_queue import CareTeamQueue
from app.database.models.escalation import Escalation, EscalationStatus
from app.database.models.escalation_action import EscalationAction
from app.database.models.escalation_assignment import EscalationAssignment
from app.database.models.patient_profile import PatientProfile
from app.database.models.queue_membership import QueueMembership
from app.database.models.staff_profile import StaffProfile
from app.database.models.user import User


class EscalationRepository:
    """Persistence boundary for nurse queue, assignment, and action data."""

    def __init__(self, db: Session):
        self.db = db

    def find_staff_by_user_id(self, user_id: int) -> Optional[StaffProfile]:
        return self.db.query(StaffProfile).filter(StaffProfile.user_id == user_id).first()

    def find_staff_by_id(self, staff_id: int) -> Optional[StaffProfile]:
        return self.db.query(StaffProfile).filter(StaffProfile.staff_id == staff_id).first()

    def find_user_by_id(self, user_id: int) -> Optional[User]:
        return self.db.query(User).filter(User.user_id == user_id).first()

    def list_escalations(self, staff_id: int, status: Optional[EscalationStatus]) -> list[Escalation]:
        query = (
            self.db.query(Escalation)
            .join(CareTeamQueue, Escalation.queue_id == CareTeamQueue.queue_id)
            .join(QueueMembership, QueueMembership.queue_id == CareTeamQueue.queue_id)
            .filter(QueueMembership.staff_id == staff_id, QueueMembership.is_active.is_(True))
        )
        if status:
            query = query.filter(Escalation.status == status)
        return query.order_by(Escalation.priority.desc(), Escalation.created_at.asc()).all()

    def find_escalation(self, escalation_id: int) -> Optional[Escalation]:
        return self.db.query(Escalation).filter(Escalation.escalation_id == escalation_id).first()

    def find_queue(self, queue_id: int) -> Optional[CareTeamQueue]:
        return self.db.query(CareTeamQueue).filter(CareTeamQueue.queue_id == queue_id).first()

    def has_active_queue_membership(self, queue_id: int, staff_id: int) -> bool:
        return (
            self.db.query(QueueMembership)
            .filter(
                QueueMembership.queue_id == queue_id,
                QueueMembership.staff_id == staff_id,
                QueueMembership.is_active.is_(True),
            )
            .first()
            is not None
        )

    def find_patient(self, patient_id: int) -> Optional[PatientProfile]:
        return self.db.query(PatientProfile).filter(PatientProfile.patient_id == patient_id).first()

    def find_active_assignment(self, escalation_id: int) -> Optional[EscalationAssignment]:
        return (
            self.db.query(EscalationAssignment)
            .filter(EscalationAssignment.escalation_id == escalation_id, EscalationAssignment.is_active.is_(True))
            .first()
        )

    def list_actions(self, escalation_id: int) -> list[EscalationAction]:
        return (
            self.db.query(EscalationAction)
            .filter(EscalationAction.escalation_id == escalation_id)
            .order_by(EscalationAction.action_at.asc())
            .all()
        )

    def add_assignment(self, assignment: EscalationAssignment) -> EscalationAssignment:
        self.db.add(assignment)
        self.db.flush()
        return assignment

    def add_action(self, action: EscalationAction) -> EscalationAction:
        self.db.add(action)
        self.db.flush()
        return action

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()

    @staticmethod
    def now() -> datetime:
        return datetime.utcnow()