"""Emergency event model."""

import enum
from sqlalchemy import Column, BigInteger, String, Boolean, ForeignKey, TIMESTAMP, Enum as SQLEnum
from sqlalchemy.sql import func
from app.database.connection import Base


class EmergencyType(enum.Enum):
    CHEST_PAIN = "CHEST_PAIN"
    BREATHING_DIFFICULTY = "BREATHING_DIFFICULTY"
    STROKE_SYMPTOMS = "STROKE_SYMPTOMS"
    SUICIDAL_IDEATION = "SUICIDAL_IDEATION"
    FALL_INJURY = "FALL_INJURY"


class EmergencyEventStatus(enum.Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class EmergencyEvent(Base):
    __tablename__ = "emergency_events"

    emergency_event_id = Column(BigInteger, primary_key=True, index=True)
    patient_id = Column(BigInteger, ForeignKey("patient_profiles.patient_id", ondelete="CASCADE"), nullable=False, index=True)
    thread_id = Column(BigInteger, ForeignKey("conversation_threads.thread_id", ondelete="CASCADE"), nullable=False, index=True)
    guardrail_hit_id = Column(BigInteger, ForeignKey("conversation_guardrail_hits.guardrail_hit_id", ondelete="CASCADE"), nullable=False, index=True)
    emergency_type = Column(SQLEnum(EmergencyType, name="emergency_type"), nullable=False, index=True)
    emergency_instruction_sent = Column(Boolean, nullable=False, server_default="false")
    notified_care_team = Column(Boolean, nullable=False, server_default="false")
    event_status = Column(SQLEnum(EmergencyEventStatus, name="emergency_event_status"), nullable=False, index=True)
    detected_at = Column(TIMESTAMP, nullable=False)
    resolved_at = Column(TIMESTAMP)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())
