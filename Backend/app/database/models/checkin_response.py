"""Structured answer captured during a patient check-in."""

import enum

from sqlalchemy import BigInteger, Column, Enum as SQLEnum, ForeignKey, Identity, Index, JSON, Text, TIMESTAMP, UniqueConstraint
from sqlalchemy.sql import func

from app.database.connection import Base
from app.database.models.checkin_question import CheckinRiskLevel


class CheckinResponseSource(enum.Enum):
    PATIENT_REPORTED = "PATIENT_REPORTED"
    STAFF_ENTERED = "STAFF_ENTERED"


class CheckinResponse(Base):
    __tablename__ = "checkin_responses"
    __table_args__ = (
        UniqueConstraint("checkin_session_id", "question_id", name="uq_checkin_responses_session_question"),
        Index("ix_checkin_responses_risk_answered", "evaluated_risk_level", "answered_at"),
    )

    response_id = Column(BigInteger, Identity(), primary_key=True)
    checkin_session_id = Column(BigInteger, ForeignKey("checkin_sessions.checkin_session_id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(BigInteger, ForeignKey("checkin_questions.question_id", ondelete="RESTRICT"), nullable=False, index=True)
    message_id = Column(BigInteger, ForeignKey("conversation_messages.message_id", ondelete="SET NULL"))
    answer_text = Column(Text)
    answer_value = Column(JSON)
    evaluated_risk_level = Column(SQLEnum(CheckinRiskLevel, name="checkin_risk_level"), nullable=False, server_default="NORMAL")
    response_source = Column(SQLEnum(CheckinResponseSource, name="checkin_response_source"), nullable=False, server_default="PATIENT_REPORTED")
    recorded_by_user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="SET NULL"))
    risk_evaluation = Column(JSON)
    answered_at = Column(TIMESTAMP, nullable=False)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())