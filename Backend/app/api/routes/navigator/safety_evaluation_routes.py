from fastapi import APIRouter,Depends,Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.response_models import SuccessResponse
from app.database.connection import get_db
from app.services.navigator.safety_evaluation_service import SafetyEvaluationService

router=APIRouter(prefix="/clinical-governance/safety-evaluations",tags=["Clinical Governance Safety Evaluations"])
class DecisionRequest(BaseModel):
    organization_id:int
    result_key:str
    decision:str
    notes:str

@router.get("",response_model=SuccessResponse)
def get_evaluations(user_id:int=Query(...,gt=0),organization_id:int|None=None,db:Session=Depends(get_db)):
    return SuccessResponse(message="Safety evaluations retrieved successfully",data=SafetyEvaluationService(db).get_overview(user_id,organization_id))

@router.post("/decisions",response_model=SuccessResponse)
def record_decision(request:DecisionRequest,user_id:int=Query(...,gt=0),db:Session=Depends(get_db)):
    SafetyEvaluationService(db).record_decision(user_id,request.organization_id,request.result_key,request.decision,request.notes)
    return SuccessResponse(message="Evaluation decision recorded",data={"result_key":request.result_key})
