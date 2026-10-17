"""Clinical guardrail rule model."""

from sqlalchemy import Column, BigInteger, String, ForeignKey, TIMESTAMP
from sqlalchemy.sql import func
from app.database.connection import Base


class ClinicalGuardrailRule(Base):
    __tablename__ = "clinical_guardrail_rules"

    rule_id = Column(BigInteger, primary_key=True, index=True)
    guardrail_id = Column(BigInteger, ForeignKey("clinical_guardrail.guardrail_id", ondelete="CASCADE"), nullable=False, index=True)
    rule_name = Column(String(255), nullable=False)
    rule_category = Column(String(50), nullable=False, index=True)
    urgency_level = Column(String(30), nullable=False, index=True)
    handler_role_id = Column(BigInteger, ForeignKey("roles.role_id", ondelete="SET NULL"), index=True)
    action_type = Column(String(50), nullable=False)
    status = Column(String(30), nullable=False, index=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp(), onupdate=func.current_timestamp())
