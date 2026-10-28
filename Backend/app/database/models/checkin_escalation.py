"""Existing check-in escalation table mapping."""

import enum

from sqlalchemy import BigInteger, Column, ForeignKey, Identity, String, Text, TIMESTAMP
from sqlalchemy.sql import func

from app.database.connection import Base


class CheckinEscalationType(enum.Enum):
    EMERGENCY = "EMERGENCY"
    ROUTINE = "ROUTINE"


class CheckinEscalationStatus(enum.Enum):
    OPEN = "OPEN"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class CheckinEscalation(Base):
    __tablename__ = "checkin_escalations"

    checkin_escalation_id = Column(BigInteger, Identity(), primary_key=True)
    checkin_session_id = Column(
        BigInteger,
        ForeignKey("checkin_sessions.checkin_session_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    response_id = Column(BigInteger, ForeignKey("checkin_responses.response_id", ondelete="SET NULL"), index=True)
    escalation_type = Column(String(9), nullable=False, index=True)
    escalation_reason = Column(Text)
    trigger_source = Column(String(30))
    matched_rule_key = Column(String(100))
    escalation_status = Column(String(11), nullable=False, index=True)
    assigned_to_staff_id = Column(
        BigInteger,
        ForeignKey("staff_profiles.staff_id", ondelete="SET NULL"),
        index=True,
    )
    assigned_at = Column(TIMESTAMP)
    resolved_at = Column(TIMESTAMP)
    action_taken = Column(Text)
    resolution_notes = Column(Text)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())
