"""Queue membership model."""

import enum
from sqlalchemy import Column, BigInteger, String, Boolean, ForeignKey, TIMESTAMP, UniqueConstraint, Enum as SQLEnum
from sqlalchemy.sql import func
from app.database.connection import Base


class QueueRole(enum.Enum):
    PRIMARY = "PRIMARY"
    BACKUP = "BACKUP"
    SUPERVISOR = "SUPERVISOR"


class QueueMembership(Base):
    __tablename__ = "queue_memberships"
    __table_args__ = (
        UniqueConstraint("queue_id", "staff_id", name="uq_queue_memberships_queue_staff"),
    )

    queue_membership_id = Column(BigInteger, primary_key=True, index=True)
    queue_id = Column(BigInteger, ForeignKey("care_team_queues.queue_id", ondelete="CASCADE"), nullable=False, index=True)
    staff_id = Column(BigInteger, ForeignKey("staff_profiles.staff_id", ondelete="CASCADE"), nullable=False, index=True)
    role_in_queue = Column(SQLEnum(QueueRole, name="queue_role"), nullable=False)
    is_active = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())
