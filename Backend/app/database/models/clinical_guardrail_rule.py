"""Clinical guardrail rule model."""

import enum
from sqlalchemy import Column, BigInteger, String, ForeignKey, TIMESTAMP, Enum as SQLEnum
from sqlalchemy.sql import func
from app.database.connection import Base


class RuleCategory(enum.Enum):
    EMERGENCY = "EMERGENCY"
    MEDICATION = "MEDICATION"
    SYMPTOM = "SYMPTOM"
    PRIVACY = "PRIVACY"
    CLINICAL_SCOPE = "CLINICAL_SCOPE"
    # Legacy compatibility
    SYMPTOM_SAFETY = "SYMPTOM_SAFETY"


class UrgencyLevel(enum.Enum):
    ROUTINE = "ROUTINE"
    SAME_DAY = "SAME_DAY"
    EMERGENCY = "EMERGENCY"
    # Legacy compatibility
    HIGH = "HIGH"


class GuardrailActionType(enum.Enum):
    SAFE_RESPOND = "SAFE_RESPOND"
    BLOCK_RESPONSE = "BLOCK_RESPONSE"
    ESCALATE = "ESCALATE"
    EMERGENCY_PROTOCOL = "EMERGENCY_PROTOCOL"
    # Legacy compatibility
    CREATE_ESCALATION = "CREATE_ESCALATION"


class RuleStatus(enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    RETIRED = "RETIRED"


class ClinicalGuardrailRule(Base):
    __tablename__ = "clinical_guardrail_rules"

    rule_id = Column(BigInteger, primary_key=True, index=True)
    guardrail_id = Column(BigInteger, ForeignKey("clinical_guardrail.guardrail_id", ondelete="CASCADE"), nullable=False, index=True)
    rule_name = Column(String(255), nullable=False)
    rule_category = Column(SQLEnum(RuleCategory, name="rule_category"), nullable=False, index=True)
    urgency_level = Column(SQLEnum(UrgencyLevel, name="urgency_level"), nullable=False, index=True)
    handler_role_id = Column(BigInteger, ForeignKey("roles.role_id", ondelete="SET NULL"), index=True)
    action_type = Column(SQLEnum(GuardrailActionType, name="guardrail_action_type"), nullable=False)
    status = Column(SQLEnum(RuleStatus, name="rule_status"), nullable=False, index=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp(), onupdate=func.current_timestamp())
