"""Care team queue model."""

import enum
from sqlalchemy import Column, BigInteger, String, ForeignKey, TIMESTAMP, Integer, Enum as SQLEnum, UniqueConstraint
from sqlalchemy.sql import func
from app.database.connection import Base


class QueueType(enum.Enum):
    MEDICATION = "MEDICATION"
    APPOINTMENT = "APPOINTMENT"
    SOCIAL_SUPPORT = "SOCIAL_SUPPORT"
    CLINICAL = "CLINICAL"
    CLINICAL_REVIEW = "CLINICAL_REVIEW"
    EMERGENCY = "EMERGENCY"


class QueueStatus(enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class CareTeamQueue(Base):
    __tablename__ = "care_team_queues"
    __table_args__ = (
        UniqueConstraint("organization_id", "role_id", name="uq_care_team_queues_org_role"),
    )

    queue_id = Column(BigInteger, primary_key=True, index=True)
    organization_id = Column(BigInteger, ForeignKey("organizations.organization_id", ondelete="CASCADE"), nullable=False, index=True)
    role_id = Column(BigInteger, ForeignKey("roles.role_id", ondelete="RESTRICT"), index=True)
    queue_name = Column(String(150), nullable=False)
    queue_type = Column(SQLEnum(QueueType, name="queue_type"), nullable=False, index=True)
    sla_minutes = Column(Integer, nullable=False)
    status = Column(SQLEnum(QueueStatus, name="queue_status"), nullable=False, index=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())
