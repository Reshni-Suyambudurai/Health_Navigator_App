"""Database-configured deterministic trigger for a clinical guardrail rule."""

import enum

from sqlalchemy import BigInteger, Boolean, Column, Enum as SQLEnum, ForeignKey, Integer, String, TIMESTAMP, UniqueConstraint
from sqlalchemy.sql import func

from app.database.connection import Base


class GuardrailMatchType(enum.Enum):
    PHRASE = "PHRASE"
    ALL_TERMS = "ALL_TERMS"


class ClinicalGuardrailMatcher(Base):
    __tablename__ = "clinical_guardrail_matchers"
    __table_args__ = (UniqueConstraint("rule_id", "pattern", name="uq_clinical_guardrail_matcher_rule_pattern"),)

    matcher_id = Column(BigInteger, primary_key=True, index=True)
    rule_id = Column(ForeignKey("clinical_guardrail_rules.rule_id", ondelete="CASCADE"), nullable=False, index=True)
    pattern = Column(String(500), nullable=False)
    match_type = Column(SQLEnum(GuardrailMatchType, name="guardrail_match_type"), nullable=False)
    priority = Column(Integer, nullable=False, server_default="100")
    is_active = Column(Boolean, nullable=False, server_default="true", index=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp(), onupdate=func.current_timestamp())