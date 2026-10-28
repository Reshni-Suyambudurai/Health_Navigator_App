from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.response_models import SuccessResponse
from app.database.connection import get_db
from app.services.navigator.safety_rules_service import SafetyRulesService

router = APIRouter(prefix="/clinical-governance/safety-rules", tags=["Clinical Governance Safety Rules"])

class ApprovalRequest(BaseModel):
    note: str

class ScenarioTestRequest(BaseModel):
    text: str
    rule_id: int | None = None

class RuleUpdateRequest(BaseModel):
    guardrail_name: str
    guardrail_markdown: str
    rule_name: str
    category: str
    urgency: str
    action_type: str
    status: str
    patient_response_template: str | None = None
    target_queue_type: str | None = None
    escalation_type: str | None = None
    escalation_priority: str | None = None

@router.get("", response_model=SuccessResponse)
def get_safety_rules(user_id: int = Query(..., gt=0), db: Session = Depends(get_db)):
    return SuccessResponse(message="Safety rules retrieved successfully", data=SafetyRulesService(db).get_overview(user_id))

@router.post("/{rule_id}/approve", response_model=SuccessResponse)
def approve_rule(rule_id: int, request: ApprovalRequest, user_id: int = Query(..., gt=0), db: Session = Depends(get_db)):
    SafetyRulesService(db).approve_rule(rule_id, user_id, request.note)
    return SuccessResponse(message="Rule approved and activated", data={"rule_id": rule_id})

@router.put("/{rule_id}", response_model=SuccessResponse)
def update_rule(rule_id: int, request: RuleUpdateRequest, user_id: int = Query(..., gt=0), db: Session = Depends(get_db)):
    SafetyRulesService(db).update_rule(rule_id, user_id, request.model_dump())
    return SuccessResponse(message="Safety rule updated successfully", data={"rule_id": rule_id})

@router.post("/scenario-test", response_model=SuccessResponse)
def test_scenario(request: ScenarioTestRequest, user_id: int = Query(..., gt=0), db: Session = Depends(get_db)):
    return SuccessResponse(message="Scenario evaluated without side effects", data=SafetyRulesService(db).test_scenario(user_id, request.text, request.rule_id))
