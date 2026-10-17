"""Emergency event model."""

from sqlalchemy import Column, BigInteger, String, Boolean, ForeignKey, TIMESTAMP
from sqlalchemy.sql import func
from app.database.connection import Base


class EmergencyEvent(Base):
    __tablename__ = "emergency_events"

    emergency_event_id = Column(BigInteger, primary_key=True, index=True)
    patient_id = Column(BigInteger, ForeignKey("patient_profiles.patient_id", ondelete="CASCADE"), nullable=False, index=True)
    thread_id = Column(BigInteger, ForeignKey("conversation_threads.thread_id", ondelete="CASCADE"), nullable=False, index=True)
    guardrail_hit_id = Column(BigInteger, ForeignKey("conversation_guardrail_hits.guardrail_hit_id", ondelete="CASCADE"), nullable=False, index=True)
    emergency_type = Column(String(50), nullable=False, index=True)
    emergency_instruction_sent = Column(Boolean, nullable=False, server_default="false")
    notified_care_team = Column(Boolean, nullable=False, server_default="false")
    event_status = Column(String(30), nullable=False, index=True)
    detected_at = Column(TIMESTAMP, nullable=False)
    resolved_at = Column(TIMESTAMP)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())
