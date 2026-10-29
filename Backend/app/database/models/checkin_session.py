"""Individual patient check-in session model."""

import enum

from sqlalchemy import BigInteger, Column, Enum as SQLEnum, ForeignKey, Identity, Index, TIMESTAMP
from sqlalchemy.sql import func

from app.database.connection import Base


class CheckinSessionStatus(enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"
    ESCALATED = "ESCALATED"
    OVERDUE = "OVERDUE"
    EXPIRED = "EXPIRED"


class CheckinSession(Base):
    __tablename__ = "checkin_sessions"
    __table_args__ = (
        Index("ix_checkin_sessions_patient_episode", "patient_id", "episode_id"),
        Index("ix_checkin_sessions_status_created", "session_status", "created_at"),
        Index("ix_checkin_sessions_scheduled_status", "scheduled_at", "session_status"),
        Index("ix_checkin_sessions_expires_at", "expires_at"),
        Index("ix_checkin_sessions_appointment_id", "appointment_id"),
    )

    checkin_session_id = Column(BigInteger, Identity(), primary_key=True)
    patient_id = Column(BigInteger, ForeignKey("patient_profiles.patient_id", ondelete="CASCADE"), nullable=False)
    episode_id = Column(BigInteger, ForeignKey("care_navigation_episodes.episode_id", ondelete="SET NULL"))
    outreach_event_id = Column(BigInteger, ForeignKey("outreach_events.outreach_event_id", ondelete="CASCADE"), nullable=False, unique=True)
    checkin_template_id = Column(BigInteger, ForeignKey("checkin_templates.checkin_template_id", ondelete="RESTRICT"), nullable=False)
    appointment_id = Column(BigInteger, ForeignKey("appointments.appointment_id", ondelete="SET NULL"), index=True)
    thread_id = Column(BigInteger, ForeignKey("conversation_threads.thread_id", ondelete="SET NULL"))
    session_status = Column(SQLEnum(CheckinSessionStatus, name="checkin_session_status"), nullable=False, server_default="PENDING")
    scheduled_at = Column(TIMESTAMP, nullable=False)
    expires_at = Column(TIMESTAMP)
    started_at = Column(TIMESTAMP)
    completed_at = Column(TIMESTAMP)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())