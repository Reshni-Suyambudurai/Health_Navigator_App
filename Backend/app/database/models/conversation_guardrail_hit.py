"""Conversation guardrail hit model."""

import enum
from sqlalchemy import Column, BigInteger, String, Text, ForeignKey, TIMESTAMP, Enum as SQLEnum
from sqlalchemy.sql import func
from app.database.connection import Base


class GuardrailHitUrgencyLevel(enum.Enum):
    ROUTINE = "ROUTINE"
    SAME_DAY = "SAME_DAY"
    EMERGENCY = "EMERGENCY"
    # Legacy compatibility
    HIGH = "HIGH"


class GuardrailActionTaken(enum.Enum):
    SAFE_RESPOND = "SAFE_RESPOND"
    BLOCK_RESPONSE = "BLOCK_RESPONSE"
    ESCALATE = "ESCALATE"
    EMERGENCY_PROTOCOL = "EMERGENCY_PROTOCOL"
    # Legacy compatibility
    ESCALATED = "ESCALATED"


class ConversationGuardrailHit(Base):
    __tablename__ = "conversation_guardrail_hits"

    guardrail_hit_id = Column(BigInteger, primary_key=True, index=True)
    thread_id = Column(BigInteger, ForeignKey("conversation_threads.thread_id", ondelete="CASCADE"), nullable=False, index=True)
    message_id = Column(BigInteger, ForeignKey("conversation_messages.message_id", ondelete="CASCADE"), nullable=False, index=True)
    patient_id = Column(BigInteger, ForeignKey("patient_profiles.patient_id", ondelete="CASCADE"), nullable=False, index=True)
    rule_id = Column(BigInteger, ForeignKey("clinical_guardrail_rules.rule_id", ondelete="CASCADE"), nullable=False, index=True)
    hit_urgency_level = Column(SQLEnum(GuardrailHitUrgencyLevel, name="guardrail_hit_urgency_level"), nullable=False, index=True)
    action_taken = Column(SQLEnum(GuardrailActionTaken, name="guardrail_action_taken"), nullable=False)
    hit_reason = Column(Text)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())
