"""Outreach campaign model."""

import enum
from sqlalchemy import Column, BigInteger, String, ForeignKey, TIMESTAMP, JSON, Enum as SQLEnum
from sqlalchemy.sql import func
from app.database.connection import Base


class CampaignType(enum.Enum):
    MEDICATION_ADHERENCE = "MEDICATION_ADHERENCE"
    APPOINTMENT_REMINDER = "APPOINTMENT_REMINDER"
    HEALTH_EDUCATION = "HEALTH_EDUCATION"
    SATISFACTION_SURVEY = "SATISFACTION_SURVEY"
    CHECK_IN = "CHECK_IN"
    # Legacy compatibility
    FOLLOW_UP = "FOLLOW_UP"


class CampaignStatus(enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


class OutreachCampaign(Base):
    __tablename__ = "outreach_campaigns"

    campaign_id = Column(BigInteger, primary_key=True, index=True)
    organization_id = Column(BigInteger, ForeignKey("organizations.organization_id", ondelete="CASCADE"), nullable=False, index=True)
    campaign_name = Column(String(200), nullable=False)
    campaign_type = Column(SQLEnum(CampaignType, name="campaign_type"), nullable=False, index=True)
    target_cohort_definition = Column(JSON)
    status = Column(SQLEnum(CampaignStatus, name="campaign_status"), nullable=False, index=True)
    created_by_user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="SET NULL"), index=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp(), onupdate=func.current_timestamp())
