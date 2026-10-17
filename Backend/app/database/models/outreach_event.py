"""Outreach event model."""

import enum
from sqlalchemy import Column, BigInteger, String, ForeignKey, TIMESTAMP, Index, Enum as SQLEnum
from sqlalchemy.sql import func
from app.database.connection import Base


class OutreachEventChannel(enum.Enum):
    SMS = "SMS"
    CALL = "CALL"
    EMAIL = "EMAIL"
    PORTAL = "PORTAL"


class OutreachEventType(enum.Enum):
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


class OutreachEvent(Base):
    __tablename__ = "outreach_events"

    outreach_event_id = Column(BigInteger, primary_key=True, index=True)
    patient_id = Column(BigInteger, ForeignKey("patient_profiles.patient_id", ondelete="CASCADE"), nullable=False, index=True)
    episode_id = Column(BigInteger, ForeignKey("care_navigation_episodes.episode_id", ondelete="CASCADE"), nullable=False, index=True)
    campaign_id = Column(BigInteger, ForeignKey("outreach_campaigns.campaign_id", ondelete="CASCADE"), nullable=False, index=True)
    workflow_id = Column(BigInteger, ForeignKey("outreach_workflows.workflow_id", ondelete="CASCADE"), nullable=False, index=True)
    channel = Column(SQLEnum(OutreachEventChannel, name="outreach_event_channel"), nullable=False)
    event_type = Column(SQLEnum(OutreachEventType, name="outreach_event_type"), nullable=False, index=True)
    delivery_status = Column(SQLEnum(DeliveryStatus, name="delivery_status"), nullable=False, index=True)
    scheduled_at = Column(TIMESTAMP)
    sent_at = Column(TIMESTAMP)
    responded_at = Column(TIMESTAMP)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())


Index("ix_outreach_events_patient_created", OutreachEvent.patient_id, OutreachEvent.created_at)
