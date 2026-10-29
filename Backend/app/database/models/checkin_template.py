"""Reusable patient check-in template model."""

import enum

from sqlalchemy import BigInteger, Boolean, Column, Enum as SQLEnum, ForeignKey, Identity, Index, Integer, String, Text, TIMESTAMP, UniqueConstraint
from sqlalchemy.sql import func

from app.database.connection import Base


class CheckinTemplateType(enum.Enum):
    POST_DISCHARGE = "POST_DISCHARGE"
    CHRONIC_CARE = "CHRONIC_CARE"
    MEDICATION_FOLLOWUP = "MEDICATION_FOLLOWUP"


class CheckinTemplateStatus(enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class CheckinTemplate(Base):
    __tablename__ = "checkin_templates"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "template_name",
            "version",
            name="uq_checkin_templates_org_name_version",
        ),
        Index("ix_checkin_templates_status", "status"),
    )

    checkin_template_id = Column(BigInteger, Identity(), primary_key=True)
    organization_id = Column(BigInteger, ForeignKey("organizations.organization_id", ondelete="RESTRICT"), nullable=False)
    escalation_role_id = Column(BigInteger, ForeignKey("roles.role_id", ondelete="SET NULL"), index=True)
    template_name = Column(String(255), nullable=False)
    template_type = Column(SQLEnum(CheckinTemplateType, name="checkin_template_type"), nullable=False)
    description = Column(Text)
    version = Column(Integer, nullable=False, server_default="1")
    status = Column(SQLEnum(CheckinTemplateStatus, name="checkin_template_status"), nullable=False, server_default="DRAFT")
    expiry_after_hours = Column(Integer)
    appointment_required = Column(Boolean, nullable=False, server_default="false")
    created_by_user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())