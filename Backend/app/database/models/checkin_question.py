"""Question belonging to a patient check-in template."""

import enum

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Column, Enum as SQLEnum, ForeignKey, Identity, Integer, JSON, String, Text, TIMESTAMP, UniqueConstraint
from sqlalchemy.sql import func

from app.database.connection import Base


class CheckinAnswerType(enum.Enum):
    YES_NO = "YES_NO"
    TEXT = "TEXT"
    NUMBER = "NUMBER"
    SINGLE_CHOICE = "SINGLE_CHOICE"
    MULTIPLE_CHOICE = "MULTIPLE_CHOICE"


class CheckinRiskLevel(enum.Enum):
    NORMAL = "NORMAL"
    ROUTINE = "ROUTINE"
    EMERGENCY = "EMERGENCY"


class CheckinQuestion(Base):
    __tablename__ = "checkin_questions"
    __table_args__ = (
        UniqueConstraint("checkin_template_id", "question_key", name="uq_checkin_questions_template_key"),
        UniqueConstraint("checkin_template_id", "display_order", name="uq_checkin_questions_template_order"),
        CheckConstraint("display_order > 0", name="chk_question_display_order"),
    )

    question_id = Column(BigInteger, Identity(), primary_key=True)
    checkin_template_id = Column(BigInteger, ForeignKey("checkin_templates.checkin_template_id", ondelete="CASCADE"), nullable=False, index=True)
    question_key = Column(String(100), nullable=False)
    question_text = Column(Text, nullable=False)
    answer_type = Column(SQLEnum(CheckinAnswerType, name="checkin_answer_type"), nullable=False)
    options = Column(JSON)
    risk_level = Column(SQLEnum(CheckinRiskLevel, name="checkin_risk_level"), nullable=False, server_default="NORMAL")
    critical_response = Column(JSON)
    display_order = Column(Integer, nullable=False)
    is_required = Column(Boolean, nullable=False, server_default="true")
    is_active = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())