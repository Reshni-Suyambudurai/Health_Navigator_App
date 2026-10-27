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

@router.get("", response_model=SuccessResponse)
def get_safety_rules(user_id: int = Query(..., gt=0), db: Session = Depends(get_db)):
    return SuccessResponse(message="Safety rules retrieved successfully", data=SafetyRulesService(db).get_overview(user_id))

@router.post("/{rule_id}/approve", response_model=SuccessResponse)
def approve_rule(rule_id: int, request: ApprovalRequest, user_id: int = Query(..., gt=0), db: Session = Depends(get_db)):
    SafetyRulesService(db).approve_rule(rule_id, user_id, request.note)
    return SuccessResponse(message="Rule approved and activated", data={"rule_id": rule_id})

@router.post("/scenario-test", response_model=SuccessResponse)
def test_scenario(request: ScenarioTestRequest, user_id: int = Query(..., gt=0), db: Session = Depends(get_db)):
    return SuccessResponse(message="Scenario evaluated without side effects", data=SafetyRulesService(db).test_scenario(user_id, request.text, request.rule_id))
