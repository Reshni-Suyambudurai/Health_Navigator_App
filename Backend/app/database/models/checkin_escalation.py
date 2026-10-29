"""Escalation created by a deterministic patient check-in rule."""

import enum

from sqlalchemy import BigInteger, Column, Enum as SQLEnum, ForeignKey, Identity, TIMESTAMP, Text, UniqueConstraint
from sqlalchemy.sql import func

from app.database.connection import Base


class CheckinEscalationType(enum.Enum):
    EMERGENCY = "EMERGENCY"
    SAME_DAY = "SAME_DAY"
    ROUTINE = "ROUTINE"


class CheckinEscalationStatus(enum.Enum):
    OPEN = "OPEN"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CANCELLED = "CANCELLED"


class CheckinEscalation(Base):
    __tablename__ = "checkin_escalations"
    __table_args__ = (
        UniqueConstraint("checkin_session_id", name="uq_checkin_escalations_session"),
    )

    checkin_escalation_id = Column(BigInteger, Identity(), primary_key=True)
    checkin_session_id = Column(
        BigInteger,
        ForeignKey("checkin_sessions.checkin_session_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    escalation_type = Column(SQLEnum(CheckinEscalationType, name="checkin_escalation_type"), nullable=False)
    escalation_reason = Column(Text, nullable=False)
    trigger_source = Column(Text)
    matched_rule_key = Column(Text)
    escalation_status = Column(
        SQLEnum(CheckinEscalationStatus, name="checkin_escalation_status"),
        nullable=False,
        server_default="OPEN",
    )
    target_role_id = Column(BigInteger, ForeignKey("roles.role_id", ondelete="SET NULL"), index=True)
    queue_id = Column(BigInteger, ForeignKey("care_team_queues.queue_id", ondelete="SET NULL"), index=True)
    assigned_to_staff_id = Column(BigInteger, ForeignKey("staff_profiles.staff_id", ondelete="SET NULL"))
    assigned_at = Column(TIMESTAMP)
    resolved_at = Column(TIMESTAMP)
    action_taken = Column(Text)
    resolution_notes = Column(Text)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())