"""Care navigation episode model."""

from sqlalchemy import Column, BigInteger, String, ForeignKey, TIMESTAMP
from sqlalchemy.sql import func
from app.database.connection import Base


class CareNavigationEpisode(Base):
    __tablename__ = "care_navigation_episodes"

    episode_id = Column(BigInteger, primary_key=True, index=True)
    patient_id = Column(BigInteger, ForeignKey("patient_profiles.patient_id", ondelete="CASCADE"), nullable=False, index=True)
    enrollment_id = Column(BigInteger, ForeignKey("patient_enrollments.enrollment_id", ondelete="CASCADE"), nullable=False, index=True)
    episode_type = Column(String(80), nullable=False, index=True)
    trigger_type = Column(String(80), nullable=False)
    trigger_reference = Column(String(255))
    status = Column(String(30), nullable=False, index=True)
    opened_at = Column(TIMESTAMP, nullable=False)
    closed_at = Column(TIMESTAMP)
    owner_staff_id = Column(BigInteger, ForeignKey("staff_profiles.staff_id", ondelete="SET NULL"), index=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp(), onupdate=func.current_timestamp())
