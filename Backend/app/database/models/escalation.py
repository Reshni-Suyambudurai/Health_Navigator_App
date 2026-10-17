"""Escalation model."""

import enum
from sqlalchemy import Column, BigInteger, String, Text, ForeignKey, TIMESTAMP, Index, Enum as SQLEnum
from sqlalchemy.sql import func
from app.database.connection import Base


class EscalationType(enum.Enum):
    MEDICATION = "MEDICATION"
    APPOINTMENT = "APPOINTMENT"
    SOCIAL_SUPPORT = "SOCIAL_SUPPORT"
    CLINICAL_REVIEW = "CLINICAL_REVIEW"
    EMERGENCY = "EMERGENCY"


class EscalationPriority(enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class EscalationStatus(enum.Enum):
    OPEN = "OPEN"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class Escalation(Base):
    __tablename__ = "escalations"

    escalation_id = Column(BigInteger, primary_key=True, index=True)
    patient_id = Column(BigInteger, ForeignKey("patient_profiles.patient_id", ondelete="CASCADE"), nullable=False, index=True)
    episode_id = Column(BigInteger, ForeignKey("care_navigation_episodes.episode_id", ondelete="CASCADE"), nullable=False, index=True)
    thread_id = Column(BigInteger, ForeignKey("conversation_threads.thread_id", ondelete="CASCADE"), nullable=False, index=True)
    guardrail_hit_id = Column(BigInteger, ForeignKey("conversation_guardrail_hits.guardrail_hit_id", ondelete="SET NULL"), index=True)
    queue_id = Column(BigInteger, ForeignKey("care_team_queues.queue_id", ondelete="CASCADE"), nullable=False, index=True)
    escalation_type = Column(SQLEnum(EscalationType, name="escalation_type"), nullable=False, index=True)
    priority = Column(SQLEnum(EscalationPriority, name="escalation_priority"), nullable=False, index=True)
    reason = Column(Text)
    patient_summary = Column(Text)
    status = Column(SQLEnum(EscalationStatus, name="escalation_status"), nullable=False, index=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())
    resolved_at = Column(TIMESTAMP)


Index("ix_escalations_queue_status", Escalation.queue_id, Escalation.status)
