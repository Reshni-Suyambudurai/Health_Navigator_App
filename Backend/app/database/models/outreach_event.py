"""Outreach event model."""

import enum
from sqlalchemy import Column, BigInteger, String, Text, ForeignKey, TIMESTAMP, Index, Integer, CheckConstraint, Enum as SQLEnum
from sqlalchemy.sql import func
from app.database.connection import Base


class OutreachEventChannel(enum.Enum):
    SMS = "SMS"
    CALL = "CALL"
    PHONE = "PHONE"
    EMAIL = "EMAIL"
    PORTAL = "PORTAL"


class OutreachEventType(enum.Enum):
    CHECK_IN = "CHECK_IN"
    APPOINTMENT_REMINDER = "APPOINTMENT_REMINDER"
    REFILL_REMINDER = "REFILL_REMINDER"
    FOLLOW_UP = "FOLLOW_UP"
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    OPENED = "OPENED"
    REPLIED = "REPLIED"
    FAILED = "FAILED"
    # Legacy compatibility
    SCHEDULED = "SCHEDULED"


class DeliveryStatus(enum.Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    RESPONDED = "RESPONDED"


class OutreachEventStatus(enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class OutreachEvent(Base):
    __tablename__ = "outreach_events"
    __table_args__ = (
        CheckConstraint("attempt_count >= 0", name="chk_outreach_attempt_count"),
        Index("ix_outreach_events_status_scheduled", "event_status", "scheduled_at"),
        Index("ix_outreach_events_patient_episode", "patient_id", "episode_id"),
        Index("ix_outreach_events_campaign_workflow", "campaign_id", "workflow_id"),
    )

    outreach_event_id = Column(BigInteger, primary_key=True, index=True)
    patient_id = Column(BigInteger, ForeignKey("patient_profiles.patient_id", ondelete="CASCADE"), nullable=False, index=True)
    episode_id = Column(BigInteger, ForeignKey("care_navigation_episodes.episode_id", ondelete="SET NULL"), index=True)
    campaign_id = Column(BigInteger, ForeignKey("outreach_campaigns.campaign_id", ondelete="CASCADE"), nullable=False, index=True)
    workflow_id = Column(BigInteger, ForeignKey("outreach_workflows.workflow_id", ondelete="CASCADE"), nullable=False, index=True)
    appointment_id = Column(BigInteger, ForeignKey("appointments.appointment_id", ondelete="SET NULL"), index=True)
    channel = Column(SQLEnum(OutreachEventChannel, name="outreach_event_channel"), nullable=False)
    event_type = Column(SQLEnum(OutreachEventType, name="outreach_event_type"), nullable=False, index=True)
    event_status = Column(SQLEnum(OutreachEventStatus, name="outreach_event_status"), nullable=False, server_default="PENDING", index=True)
    delivery_status = Column(SQLEnum(DeliveryStatus, name="delivery_status"), nullable=False, server_default="PENDING", index=True)
    scheduled_at = Column(TIMESTAMP, nullable=False)
    sent_at = Column(TIMESTAMP)
    responded_at = Column(TIMESTAMP)
    completed_at = Column(TIMESTAMP)
    attempt_count = Column(Integer, nullable=False, server_default="0")
    last_error = Column(Text)
    idempotency_key = Column(String(255), nullable=False, unique=True, index=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())


Index("ix_outreach_events_patient_created", OutreachEvent.patient_id, OutreachEvent.created_at)
