"""Nurse escalation queue HTTP routes."""

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.response_models import SuccessResponse
from app.database.connection import get_db
from app.services.navigator.escalation_service import EscalationService


router = APIRouter(prefix="/escalations", tags=["Escalations"])


class EscalationActionRequest(BaseModel):
    nurse_user_id: int = Field(gt=0)
    action_type: str
    notes: Optional[str] = Field(default=None, max_length=2000)


class EscalationResolveRequest(BaseModel):
    nurse_user_id: int = Field(gt=0)
    notes: Optional[str] = Field(default=None, max_length=2000)


@router.get("", response_model=SuccessResponse)
async def list_escalations(nurse_user_id: int, status: Optional[str] = None, db: Session = Depends(get_db)):
    escalations = EscalationService(db).list_for_nurse(nurse_user_id, status)
    return SuccessResponse(status="success", message="Escalation queue retrieved successfully", data={"escalations": escalations, "count": len(escalations)})


@router.get("/{escalation_id}", response_model=SuccessResponse)
async def get_escalation(escalation_id: int, nurse_user_id: int, db: Session = Depends(get_db)):
    return SuccessResponse(status="success", message="Escalation retrieved successfully", data=EscalationService(db).get_detail(nurse_user_id, escalation_id))


@router.post("/{escalation_id}/claim", response_model=SuccessResponse)
async def claim_escalation(escalation_id: int, nurse_user_id: int, db: Session = Depends(get_db)):
    return SuccessResponse(status="success", message="Escalation claimed successfully", data=EscalationService(db).claim(nurse_user_id, escalation_id))


@router.post("/{escalation_id}/actions", response_model=SuccessResponse)
async def add_escalation_action(escalation_id: int, payload: EscalationActionRequest, db: Session = Depends(get_db)):
    data = EscalationService(db).add_action(payload.nurse_user_id, escalation_id, payload.action_type, payload.notes)
    return SuccessResponse(status="success", message="Escalation action recorded successfully", data=data)


@router.post("/{escalation_id}/resolve", response_model=SuccessResponse)
async def resolve_escalation(escalation_id: int, payload: EscalationResolveRequest, db: Session = Depends(get_db)):
    data = EscalationService(db).resolve(payload.nurse_user_id, escalation_id, payload.notes)
    return SuccessResponse(status="success", message="Escalation resolved successfully", data=data)