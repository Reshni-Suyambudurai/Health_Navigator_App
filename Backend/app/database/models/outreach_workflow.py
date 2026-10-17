"""Outreach workflow model."""

from sqlalchemy import Column, BigInteger, String, Text, Boolean, ForeignKey, TIMESTAMP, Integer, UniqueConstraint
from sqlalchemy.sql import func
from app.database.connection import Base


class OutreachWorkflow(Base):
    __tablename__ = "outreach_workflows"
    __table_args__ = (
        UniqueConstraint("campaign_id", "step_order", name="uq_outreach_workflows_campaign_step"),
    )

    workflow_id = Column(BigInteger, primary_key=True, index=True)
    campaign_id = Column(BigInteger, ForeignKey("outreach_campaigns.campaign_id", ondelete="CASCADE"), nullable=False, index=True)
    step_order = Column(Integer, nullable=False)
    step_name = Column(String(120), nullable=False)
    trigger_offset_hours = Column(Integer, nullable=False)
    channel = Column(String(30), nullable=False)
    template_text = Column(Text, nullable=False)
    escalation_on_no_response = Column(Boolean, nullable=False, server_default="false")
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())
