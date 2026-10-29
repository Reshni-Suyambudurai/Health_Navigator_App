"""Escalation assignment model."""

import enum

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Column, Enum as SQLEnum, ForeignKey, Text, TIMESTAMP, UniqueConstraint
from app.database.connection import Base


class EscalationAssignmentStatus(enum.Enum):
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class EscalationAssignment(Base):
    __tablename__ = "escalation_assignments"
    __table_args__ = (
        CheckConstraint(
            "(escalation_id IS NOT NULL) <> (checkin_escalation_id IS NOT NULL)",
            name="chk_escalation_assignments_single_parent",
        ),
        UniqueConstraint("checkin_escalation_id", name="uq_escalation_assignments_checkin"),
    )

    assignment_id = Column(BigInteger, primary_key=True, index=True)
    escalation_id = Column(BigInteger, ForeignKey("escalations.escalation_id", ondelete="CASCADE"), index=True)
    checkin_escalation_id = Column(
        BigInteger,
        ForeignKey("checkin_escalations.checkin_escalation_id", ondelete="CASCADE"),
        index=True,
    )
    assigned_to_staff_id = Column(BigInteger, ForeignKey("staff_profiles.staff_id", ondelete="SET NULL"), index=True)
    assigned_by_user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="SET NULL"), index=True)
    assigned_at = Column(TIMESTAMP, nullable=False)
    unassigned_at = Column(TIMESTAMP)
    is_active = Column(Boolean, nullable=False, server_default="true", index=True)
    assignment_status = Column(
        SQLEnum(EscalationAssignmentStatus, name="escalation_assignment_status"),
        nullable=False,
        server_default="ASSIGNED",
        index=True,
    )
    action_taken = Column(Text)
    resolution_notes = Column(Text)
    completed_at = Column(TIMESTAMP)
