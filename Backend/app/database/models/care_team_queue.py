"""Care team queue model."""

from sqlalchemy import Column, BigInteger, String, ForeignKey, TIMESTAMP, Integer
from sqlalchemy.sql import func
from app.database.connection import Base


class CareTeamQueue(Base):
    __tablename__ = "care_team_queues"

    queue_id = Column(BigInteger, primary_key=True, index=True)
    organization_id = Column(BigInteger, ForeignKey("organizations.organization_id", ondelete="CASCADE"), nullable=False, index=True)
    queue_name = Column(String(150), nullable=False)
    queue_type = Column(String(40), nullable=False, index=True)
    sla_minutes = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False, index=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())
