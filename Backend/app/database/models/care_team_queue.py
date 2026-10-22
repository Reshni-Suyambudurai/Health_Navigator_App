"""Care team queue model."""

import enum
from sqlalchemy import Column, BigInteger, String, ForeignKey, TIMESTAMP, Integer, Enum as SQLEnum
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

    queue_id = Column(BigInteger, primary_key=True, index=True)
    organization_id = Column(BigInteger, ForeignKey("organizations.organization_id", ondelete="CASCADE"), nullable=False, index=True)
    queue_name = Column(String(150), nullable=False)
    queue_type = Column(SQLEnum(QueueType, name="queue_type"), nullable=False, index=True)
    sla_minutes = Column(Integer, nullable=False)
    status = Column(SQLEnum(QueueStatus, name="queue_status"), nullable=False, index=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())
