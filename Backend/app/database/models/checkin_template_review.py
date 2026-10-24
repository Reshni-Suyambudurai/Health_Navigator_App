"""Clinical review history for check-in template versions."""

import enum

from sqlalchemy import BigInteger, Column, Enum as SQLEnum, ForeignKey, Identity, Index, String, Text, TIMESTAMP
from sqlalchemy.sql import func

from app.database.connection import Base


class CheckinTemplateReviewStatus(enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class CheckinTemplateReview(Base):
    __tablename__ = "checkin_template_reviews"
    __table_args__ = (
        Index("ix_checkin_template_reviews_template_created", "checkin_template_id", "created_at"),
        Index("ix_checkin_template_reviews_status", "status"),
    )

    review_id = Column(BigInteger, Identity(), primary_key=True)
    checkin_template_id = Column(
        BigInteger,
        ForeignKey("checkin_templates.checkin_template_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    submitted_by_user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False)
    reviewed_by_user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="SET NULL"))
    status = Column(
        SQLEnum(CheckinTemplateReviewStatus, name="checkin_template_review_status"),
        nullable=False,
        server_default="PENDING",
    )
    submission_note = Column(String(1000))
    review_notes = Column(Text)
    submitted_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())
    reviewed_at = Column(TIMESTAMP)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())