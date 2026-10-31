"""Database access for clinical-governance dashboard analytics."""

from datetime import datetime

from sqlalchemy import exists, or_
from sqlalchemy.orm import Session

from app.database.models.audit_log import AuditLog
from app.database.models.clinical_guardrail_rule import ClinicalGuardrailRule
from app.database.models.conversation_guardrail_hit import ConversationGuardrailHit
from app.database.models.conversation_message import ConversationMessage
from app.database.models.emergency_event import EmergencyEvent
from app.database.models.escalation import Escalation
from app.database.models.escalation_action import EscalationAction
from app.database.models.escalation_assignment import EscalationAssignment
from app.database.models.patient_enrollment import PatientEnrollment
from app.database.models.patient_profile import PatientProfile
from app.database.models.role import Role
from app.database.models.user import User


class ClinicalGovernanceDashboardRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_context(self, user_id: int):
        return (
            self.db.query(User, Role)
            .join(Role, Role.role_id == User.role_id)
            .filter(User.user_id == user_id)
            .first()
        )

    def list_guardrail_hits(self, organization_id: int, start_at: datetime, end_at: datetime):
        return (
            self.db.query(
                ConversationGuardrailHit,
                ClinicalGuardrailRule,
                ConversationMessage,
                EmergencyEvent,
            )
            .join(
                ClinicalGuardrailRule,
                ClinicalGuardrailRule.rule_id == ConversationGuardrailHit.rule_id,
            )
            .join(
                ConversationMessage,
                ConversationMessage.message_id == ConversationGuardrailHit.message_id,
            )
            .outerjoin(
                EmergencyEvent,
                EmergencyEvent.guardrail_hit_id == ConversationGuardrailHit.guardrail_hit_id,
            )
            .filter(
                exists().where(
                    PatientEnrollment.patient_id == ConversationGuardrailHit.patient_id,
                    PatientEnrollment.organization_id == organization_id,
                ),
                ConversationGuardrailHit.created_at >= start_at,
                ConversationGuardrailHit.created_at < end_at,
            )
            .distinct(ConversationGuardrailHit.guardrail_hit_id)
            .order_by(
                ConversationGuardrailHit.guardrail_hit_id,
                ConversationGuardrailHit.created_at.desc(),
            )
            .all()
        )

    def list_rules(self):
        return (
            self.db.query(ClinicalGuardrailRule)
            .order_by(ClinicalGuardrailRule.rule_name.asc())
            .all()
        )

    def list_escalations(self, organization_id: int, start_at: datetime, end_at: datetime):
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
                    PatientEnrollment.patient_id == Escalation.patient_id,
                    PatientEnrollment.organization_id == organization_id,
                ),
                Escalation.created_at >= start_at,
                Escalation.created_at < end_at,
            )
            .distinct(Escalation.escalation_id)
            .order_by(Escalation.escalation_id, Escalation.created_at.desc())
            .all()
        )

    def list_assignments(self, escalation_ids: list[int]):
        if not escalation_ids:
            return []
        return self.db.query(EscalationAssignment).filter(
            EscalationAssignment.escalation_id.in_(escalation_ids),
            EscalationAssignment.is_active.is_(True),
        ).all()

    def list_actions(self, escalation_ids: list[int]):
        if not escalation_ids:
            return []
        return (
            self.db.query(EscalationAction)
            .filter(EscalationAction.escalation_id.in_(escalation_ids))
            .order_by(EscalationAction.action_at.desc())
            .all()
        )

    def list_audit_history(self, organization_id: int, start_at: datetime, end_at: datetime):
        return (
            self.db.query(AuditLog, User)
            .outerjoin(User, User.user_id == AuditLog.user_id)
            .filter(
                AuditLog.created_at >= start_at,
                AuditLog.created_at < end_at,
                AuditLog.action.in_([
                    "CREATE_ESCALATION",
                    "UPDATE_ESCALATION",
                    "CLOSE_ESCALATION",
                    "UPDATE_CARE_PLAN",
                ]),
                or_(
                    User.organization_id == organization_id,
                    exists().where(
                        PatientEnrollment.patient_id == AuditLog.patient_id,
                        PatientEnrollment.organization_id == organization_id,
                    ),
                ),
            )
            .distinct(AuditLog.audit_id)
            .order_by(AuditLog.audit_id, AuditLog.created_at.desc())
            .all()
        )