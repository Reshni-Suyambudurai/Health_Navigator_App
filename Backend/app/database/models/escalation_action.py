"""Escalation action model."""

from sqlalchemy import Column, BigInteger, String, Text, ForeignKey, TIMESTAMP
from app.database.connection import Base


class EscalationAction(Base):
    __tablename__ = "escalation_actions"

    escalation_action_id = Column(BigInteger, primary_key=True, index=True)
    escalation_id = Column(BigInteger, ForeignKey("escalations.escalation_id", ondelete="CASCADE"), nullable=False, index=True)
    action_by_user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="SET NULL"), index=True)
    action_type = Column(String(40), nullable=False, index=True)
    action_notes = Column(Text)
    action_at = Column(TIMESTAMP, nullable=False, index=True)
