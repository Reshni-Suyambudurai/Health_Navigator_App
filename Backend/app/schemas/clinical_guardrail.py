"""Request contracts for clinical guardrail management."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


RuleCategory = Literal[
    "EMERGENCY",
    "MEDICATION",
    "SYMPTOM",
    "PRIVACY",
    "CLINICAL_SCOPE",
    "SYMPTOM_SAFETY",
]
UrgencyLevel = Literal["ROUTINE", "SAME_DAY", "EMERGENCY", "HIGH"]
ActionType = Literal[
    "SAFE_RESPOND",
    "BLOCK_RESPONSE",
    "ESCALATE",
    "EMERGENCY_PROTOCOL",
    "CREATE_ESCALATION",
]
QueueType = Literal[
    "MEDICATION",
    "APPOINTMENT",
    "SOCIAL_SUPPORT",
    "CLINICAL",
    "CLINICAL_REVIEW",
    "EMERGENCY",
]
EscalationType = Literal[
    "MEDICATION",
    "APPOINTMENT",
    "SOCIAL_SUPPORT",
    "CLINICAL_REVIEW",
    "EMERGENCY",
]
EscalationPriority = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]


class GuardrailRulePayload(BaseModel):
    rule_name: str = Field(min_length=1, max_length=255)
    category: RuleCategory
    urgency: UrgencyLevel
    handler_role_id: int | None = Field(default=None, gt=0)
    action_type: ActionType
    patient_response_template: str | None = Field(default=None, max_length=4000)
    target_queue_type: QueueType | None = None
    escalation_type: EscalationType | None = None
    escalation_priority: EscalationPriority | None = None


class ClinicalGuardrailCreateRequest(BaseModel):
    guardrail_name: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1, max_length=10000)
    rules: list[GuardrailRulePayload] = Field(min_length=1)


class ClinicalGuardrailRuleCreateRequest(GuardrailRulePayload):
    pass


class ClinicalGuardrailRuleUpdateRequest(GuardrailRulePayload):
    guardrail_name: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1, max_length=10000)


class ClinicalGuardrailSubmitRequest(BaseModel):
    rule_ids: list[int] = Field(min_length=1)


class ClinicalGuardrailApprovalRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=4000)
    effective_from: date


class ClinicalGuardrailRejectionRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=4000)


class ClinicalGuardrailReasonRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=4000)


class ClinicalGuardrailActivationRequest(ClinicalGuardrailRuleUpdateRequest):
    change_reason: str = Field(min_length=1, max_length=4000)
    effective_from: date