"""Outreach workflow model."""

import enum
from sqlalchemy import Column, BigInteger, String, Text, Boolean, ForeignKey, TIMESTAMP, Integer, UniqueConstraint, CheckConstraint, Enum as SQLEnum
from sqlalchemy.sql import func
from app.database.connection import Base


class OutreachChannel(enum.Enum):
    SMS = "SMS"
    CALL = "CALL"
    PHONE = "PHONE"
    EMAIL = "EMAIL"
    PORTAL = "PORTAL"


class TriggerType(enum.Enum):
    AFTER_DISCHARGE = "AFTER_DISCHARGE"
    BEFORE_APPOINTMENT = "BEFORE_APPOINTMENT"
    AFTER_EVENT = "AFTER_EVENT"


class TriggerAnchor(enum.Enum):
    DISCHARGE_DATETIME = "DISCHARGE_DATETIME"
    APPOINTMENT_DATETIME = "APPOINTMENT_DATETIME"
    EVENT_DATETIME = "EVENT_DATETIME"


class OutreachWorkflow(Base):
    __tablename__ = "outreach_workflows"
    __table_args__ = (
        UniqueConstraint("campaign_id", "step_order", name="uq_outreach_workflows_campaign_step"),
        CheckConstraint("step_order > 0", name="chk_workflow_step_order"),
        CheckConstraint("trigger_offset_hours >= 0", name="chk_trigger_offset"),
        CheckConstraint("max_attempts > 0", name="chk_max_attempts"),
        CheckConstraint("retry_interval_minutes >= 0", name="chk_retry_interval"),
    )

    workflow_id = Column(BigInteger, primary_key=True, index=True)
    campaign_id = Column(BigInteger, ForeignKey("outreach_campaigns.campaign_id", ondelete="CASCADE"), nullable=False, index=True)
    step_order = Column(Integer, nullable=False)
    step_name = Column(String(255), nullable=False)
    trigger_type = Column(SQLEnum(TriggerType, name="outreach_trigger_type"), nullable=False)
    trigger_anchor = Column(SQLEnum(TriggerAnchor, name="outreach_trigger_anchor"), nullable=False)
    trigger_offset_hours = Column(Integer, nullable=False, server_default="0")
    channel = Column(SQLEnum(OutreachChannel, name="outreach_channel"), nullable=False)
    template_text = Column(Text)
    checkin_template_id = Column(BigInteger, ForeignKey("checkin_templates.checkin_template_id", ondelete="SET NULL"), index=True)
    escalation_on_no_response = Column(Boolean, nullable=False, server_default="false")
    max_attempts = Column(Integer, nullable=False, server_default="3")
    retry_interval_minutes = Column(Integer, nullable=False, server_default="30")
    is_active = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())
