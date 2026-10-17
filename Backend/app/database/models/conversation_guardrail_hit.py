"""Conversation guardrail hit model."""

from sqlalchemy import Column, BigInteger, String, Text, ForeignKey, TIMESTAMP
from sqlalchemy.sql import func
from app.database.connection import Base


class ConversationGuardrailHit(Base):
    __tablename__ = "conversation_guardrail_hits"

    guardrail_hit_id = Column(BigInteger, primary_key=True, index=True)
    thread_id = Column(BigInteger, ForeignKey("conversation_threads.thread_id", ondelete="CASCADE"), nullable=False, index=True)
    message_id = Column(BigInteger, ForeignKey("conversation_messages.message_id", ondelete="CASCADE"), nullable=False, index=True)
    patient_id = Column(BigInteger, ForeignKey("patient_profiles.patient_id", ondelete="CASCADE"), nullable=False, index=True)
    rule_id = Column(BigInteger, ForeignKey("clinical_guardrail_rules.rule_id", ondelete="CASCADE"), nullable=False, index=True)
    hit_urgency_level = Column(String(30), nullable=False, index=True)
    action_taken = Column(String(50), nullable=False)
    hit_reason = Column(Text)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())
