"""HTTP routes for clinical guardrail management."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.response_models import SuccessResponse
from app.database.connection import get_db
from app.schemas.clinical_guardrail import (
    ClinicalGuardrailActivationRequest,
    ClinicalGuardrailApprovalRequest,
    ClinicalGuardrailCreateRequest,
    ClinicalGuardrailReasonRequest,
    ClinicalGuardrailRejectionRequest,
    ClinicalGuardrailRuleCreateRequest,
    ClinicalGuardrailRuleUpdateRequest,
    ClinicalGuardrailSubmitRequest,
)
from app.services.clinical_guardrail_service import ClinicalGuardrailService


router = APIRouter(prefix="/clinical-guardrails", tags=["Clinical Guardrails"])


@router.get("", response_model=SuccessResponse)
def list_guardrails(
    user_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
):
    data = ClinicalGuardrailService(db).get_overview(user_id)
    return SuccessResponse(message="Clinical guardrails retrieved successfully", data=data)


@router.post("", response_model=SuccessResponse)
def create_guardrail(
    request: ClinicalGuardrailCreateRequest,
    user_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
):
    data = ClinicalGuardrailService(db).create_guardrail(user_id, request.model_dump())
    return SuccessResponse(message="Clinical guardrail created as draft", data=data)


@router.post("/{guardrail_id}/rules", response_model=SuccessResponse)
def add_rule(
    guardrail_id: int,
    request: ClinicalGuardrailRuleCreateRequest,
    user_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
):
    data = ClinicalGuardrailService(db).add_rule(guardrail_id, user_id, request.model_dump())
    return SuccessResponse(message="Clinical guardrail rule created as draft", data=data)


@router.post("/rules/submit", response_model=SuccessResponse)
def submit_rules(
    request: ClinicalGuardrailSubmitRequest,
    user_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
):
    data = ClinicalGuardrailService(db).submit_rules(user_id, request.rule_ids)
    return SuccessResponse(message="Clinical guardrail rules submitted for review", data=data)


@router.put("/rules/{rule_id}", response_model=SuccessResponse)
def update_draft_rule(
    rule_id: int,
    request: ClinicalGuardrailRuleUpdateRequest,
    user_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
):
    data = ClinicalGuardrailService(db).update_draft_rule(rule_id, user_id, request.model_dump())
    return SuccessResponse(message="Clinical guardrail rule updated", data=data)


@router.post("/rules/{rule_id}/approve", response_model=SuccessResponse)
def approve_rule(
    rule_id: int,
    request: ClinicalGuardrailApprovalRequest,
    user_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
):
    data = ClinicalGuardrailService(db).approve_rule(
        rule_id,
        user_id,
        request.reason,
        request.effective_from,
    )
    return SuccessResponse(message="Clinical guardrail rule approved", data=data)


@router.post("/rules/{rule_id}/reject", response_model=SuccessResponse)
def reject_rule(
    rule_id: int,
    request: ClinicalGuardrailRejectionRequest,
    user_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
):
    data = ClinicalGuardrailService(db).reject_rule(rule_id, user_id, request.reason)
    return SuccessResponse(message="Clinical guardrail rule rejected", data=data)


@router.post("/rules/{rule_id}/deactivate", response_model=SuccessResponse)
def deactivate_rule(
    rule_id: int,
    request: ClinicalGuardrailReasonRequest,
    user_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
):
    data = ClinicalGuardrailService(db).deactivate_rule(rule_id, user_id, request.reason)
    return SuccessResponse(message="Clinical guardrail rule deactivated", data=data)


@router.put("/rules/{rule_id}/activate", response_model=SuccessResponse)
def activate_updated_rule(
    rule_id: int,
    request: ClinicalGuardrailActivationRequest,
    user_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
):
    values = request.model_dump(exclude={"change_reason", "effective_from"})
    data = ClinicalGuardrailService(db).activate_updated_rule(
        rule_id,
        user_id,
        values,
        request.change_reason,
        request.effective_from,
    )
    return SuccessResponse(message="Clinical guardrail rule updated and activated", data=data)