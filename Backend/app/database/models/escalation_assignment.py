"""Escalation assignment model."""

from sqlalchemy import Column, BigInteger, Boolean, ForeignKey, TIMESTAMP
from app.database.connection import Base


class EscalationAssignment(Base):
    __tablename__ = "escalation_assignments"

    assignment_id = Column(BigInteger, primary_key=True, index=True)
    escalation_id = Column(BigInteger, ForeignKey("escalations.escalation_id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_to_staff_id = Column(BigInteger, ForeignKey("staff_profiles.staff_id", ondelete="SET NULL"), index=True)
    assigned_by_user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="SET NULL"), index=True)
    assigned_at = Column(TIMESTAMP, nullable=False)
    unassigned_at = Column(TIMESTAMP)
    is_active = Column(Boolean, nullable=False, server_default="true", index=True)
