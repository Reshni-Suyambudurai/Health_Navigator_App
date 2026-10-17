"""Escalation model."""

from sqlalchemy import Column, BigInteger, String, Text, ForeignKey, TIMESTAMP, Index
from sqlalchemy.sql import func
from app.database.connection import Base


class Escalation(Base):
    __tablename__ = "escalations"

    escalation_id = Column(BigInteger, primary_key=True, index=True)
    patient_id = Column(BigInteger, ForeignKey("patient_profiles.patient_id", ondelete="CASCADE"), nullable=False, index=True)
    episode_id = Column(BigInteger, ForeignKey("care_navigation_episodes.episode_id", ondelete="CASCADE"), nullable=False, index=True)
    thread_id = Column(BigInteger, ForeignKey("conversation_threads.thread_id", ondelete="CASCADE"), nullable=False, index=True)
    guardrail_hit_id = Column(BigInteger, ForeignKey("conversation_guardrail_hits.guardrail_hit_id", ondelete="SET NULL"), index=True)
    queue_id = Column(BigInteger, ForeignKey("care_team_queues.queue_id", ondelete="CASCADE"), nullable=False, index=True)
    escalation_type = Column(String(40), nullable=False, index=True)
    priority = Column(String(20), nullable=False, index=True)
    reason = Column(Text)
    patient_summary = Column(Text)
    status = Column(String(30), nullable=False, index=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())
    resolved_at = Column(TIMESTAMP)


Index("ix_escalations_queue_status", Escalation.queue_id, Escalation.status)
