"""Outreach event model."""

from sqlalchemy import Column, BigInteger, String, ForeignKey, TIMESTAMP, Index
from sqlalchemy.sql import func
from app.database.connection import Base


class OutreachEvent(Base):
    __tablename__ = "outreach_events"

    outreach_event_id = Column(BigInteger, primary_key=True, index=True)
    patient_id = Column(BigInteger, ForeignKey("patient_profiles.patient_id", ondelete="CASCADE"), nullable=False, index=True)
    episode_id = Column(BigInteger, ForeignKey("care_navigation_episodes.episode_id", ondelete="CASCADE"), nullable=False, index=True)
    campaign_id = Column(BigInteger, ForeignKey("outreach_campaigns.campaign_id", ondelete="CASCADE"), nullable=False, index=True)
    workflow_id = Column(BigInteger, ForeignKey("outreach_workflows.workflow_id", ondelete="CASCADE"), nullable=False, index=True)
    channel = Column(String(30), nullable=False)
    event_type = Column(String(40), nullable=False, index=True)
    delivery_status = Column(String(20), nullable=False, index=True)
    scheduled_at = Column(TIMESTAMP)
    sent_at = Column(TIMESTAMP)
    responded_at = Column(TIMESTAMP)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())


Index("ix_outreach_events_patient_created", OutreachEvent.patient_id, OutreachEvent.created_at)
