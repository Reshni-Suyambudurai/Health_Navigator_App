"""Outreach campaign model."""

from sqlalchemy import Column, BigInteger, String, ForeignKey, TIMESTAMP, JSON
from sqlalchemy.sql import func
from app.database.connection import Base


class OutreachCampaign(Base):
    __tablename__ = "outreach_campaigns"

    campaign_id = Column(BigInteger, primary_key=True, index=True)
    organization_id = Column(BigInteger, ForeignKey("organizations.organization_id", ondelete="CASCADE"), nullable=False, index=True)
    campaign_name = Column(String(200), nullable=False)
    campaign_type = Column(String(50), nullable=False, index=True)
    target_cohort_definition = Column(JSON)
    status = Column(String(30), nullable=False, index=True)
    created_by_user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="SET NULL"), index=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp(), onupdate=func.current_timestamp())
