"""HTTP endpoints for outreach, check-ins, and follow-up work."""

from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.response_models import SuccessResponse
from app.database.connection import get_db
from app.services.navigator.outreach_service import OutreachService


router = APIRouter(prefix="/outreach", tags=["Outreach"])


class CampaignCreateRequest(BaseModel):
    organization_id: int = Field(gt=0)
    campaign_name: str = Field(min_length=1, max_length=255)
    campaign_type: str
    target_cohort_definition: dict[str, Any] | None = None
    timezone: str = "UTC"
    start_at: datetime | None = None
    end_at: datetime | None = None
    status: str = "DRAFT"


class CampaignUpdateRequest(BaseModel):
    campaign_name: str | None = Field(default=None, min_length=1, max_length=255)
    campaign_type: str | None = None
    target_cohort_definition: dict[str, Any] | None = None
    timezone: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    status: str | None = None


class WorkflowRequest(BaseModel):
    step_order: int = Field(gt=0)
    step_name: str = Field(min_length=1, max_length=255)
    trigger_type: str
    trigger_anchor: str
    trigger_offset_hours: int = Field(default=0, ge=0)
    channel: str
    template_text: str | None = None
    checkin_template_id: int | None = Field(default=None, gt=0)
    escalation_on_no_response: bool = False
    max_attempts: int = Field(default=3, gt=0)
    retry_interval_minutes: int = Field(default=30, ge=0)
    is_active: bool = True


class WorkflowUpdateRequest(BaseModel):
    step_order: int | None = Field(default=None, gt=0)
    step_name: str | None = Field(default=None, min_length=1, max_length=255)
    trigger_type: str | None = None
    trigger_anchor: str | None = None
    trigger_offset_hours: int | None = Field(default=None, ge=0)
    channel: str | None = None
    template_text: str | None = None
    checkin_template_id: int | None = Field(default=None, gt=0)
    escalation_on_no_response: bool | None = None
    max_attempts: int | None = Field(default=None, gt=0)
    retry_interval_minutes: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class CheckinTemplateRequest(BaseModel):
    organization_id: int = Field(gt=0)
    template_name: str = Field(min_length=1, max_length=255)
    template_type: str
    description: str | None = None
    version: int = Field(default=1, gt=0)
    status: Literal["DRAFT", "ACTIVE", "INACTIVE"] = "DRAFT"


class CheckinQuestionRequest(BaseModel):
    question_key: str = Field(min_length=1, max_length=100)
    question_text: str = Field(min_length=1)
    answer_type: Literal["YES_NO", "TEXT", "NUMBER", "SINGLE_CHOICE", "MULTIPLE_CHOICE"]
    options: list[Any] | dict[str, Any] | None = None
    display_order: int = Field(gt=0)
    is_required: bool = True
    is_active: bool = True


class OutreachEventCreateRequest(BaseModel):
    patient_id: int = Field(gt=0)
    episode_id: int | None = Field(default=None, gt=0)
    campaign_id: int = Field(gt=0)
    workflow_id: int = Field(gt=0)
    appointment_id: int | None = Field(default=None, gt=0)
    channel: str
    event_type: str
    event_status: str = "PENDING"
    delivery_status: str = "PENDING"
    scheduled_at: datetime
    idempotency_key: str = Field(min_length=1, max_length=255)


class OutreachEventUpdateRequest(BaseModel):
    appointment_id: int | None = Field(default=None, gt=0)
    event_status: str | None = None
    delivery_status: str | None = None
    scheduled_at: datetime | None = None
    sent_at: datetime | None = None
    responded_at: datetime | None = None
    completed_at: datetime | None = None
    attempt_count: int | None = Field(default=None, ge=0)
    last_error: str | None = None


class CheckinSessionRequest(BaseModel):
    patient_id: int = Field(gt=0)
    episode_id: int | None = Field(default=None, gt=0)
    outreach_event_id: int = Field(gt=0)
    checkin_template_id: int = Field(gt=0)
    thread_id: int | None = Field(default=None, gt=0)
    session_status: Literal["PENDING", "IN_PROGRESS", "COMPLETED", "ABANDONED", "ESCALATED"] = "PENDING"
    started_at: datetime | None = None
    completed_at: datetime | None = None


class CheckinResponseRequest(BaseModel):
    question_id: int = Field(gt=0)
    message_id: int | None = Field(default=None, gt=0)
    answer_text: str | None = None
    answer_value: Any | None = None
    response_source: Literal["PATIENT_REPORTED", "STAFF_ENTERED"] = "PATIENT_REPORTED"
    answered_at: datetime


class AppointmentActionRequest(BaseModel):
    contact_datetime: datetime | None = None
    contact_method: Literal["PHONE", "PORTAL", "SMS", "VIDEO", "IN_PERSON", "INTERNAL_REVIEW"] | None = None
    action_taken: Literal["REVIEWED", "CALL_ATTEMPT", "PATIENT_CONTACTED", "GUIDANCE_PROVIDED", "REFERRED", "OTHER"]
    outcome: Literal["REACHED", "NO_ANSWER", "ISSUE_ADDRESSED", "ISSUE_UNRESOLVED", "REFERRED", "OTHER"] | None = None
    action_notes: str | None = None
    resolution_status: Literal["PENDING", "RESOLVED", "FOLLOW_UP_REQUIRED", "UNABLE_TO_REACH"] = "PENDING"
    follow_up_required: bool = False
    follow_up_notes: str | None = None
    follow_up_due_at: datetime | None = None


class FollowUpTaskRequest(BaseModel):
    patient_id: int = Field(gt=0)
    episode_id: int | None = Field(default=None, gt=0)
    appointment_id: int | None = Field(default=None, gt=0)
    escalation_id: int | None = Field(default=None, gt=0)
    task_type: Literal["PATIENT_CONTACT", "MEDICATION_FOLLOWUP", "APPOINTMENT_BOOKING", "CLINICAL_REVIEW", "OTHER"]
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    assigned_to_staff_id: int | None = Field(default=None, gt=0)
    due_at: datetime | None = None
    priority: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = "MEDIUM"
    status: Literal["OPEN", "IN_PROGRESS", "COMPLETED", "CANCELLED"] = "OPEN"


class FollowUpTaskUpdateRequest(BaseModel):
    assigned_to_staff_id: int | None = Field(default=None, gt=0)
    due_at: datetime | None = None
    priority: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] | None = None
    status: Literal["OPEN", "IN_PROGRESS", "COMPLETED", "CANCELLED"] | None = None
    completion_notes: str | None = None


@router.get("/campaigns", response_model=SuccessResponse)
def list_campaigns(
    organization_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
):
    records = OutreachService(db).list_campaigns(organization_id)
    return SuccessResponse(message="Campaigns retrieved successfully", data={"campaigns": records, "count": len(records)})


@router.post("/campaigns", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
def create_campaign(
    request: CampaignCreateRequest,
    user_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
):
    record = OutreachService(db).create_campaign(request.model_dump(), user_id)
    return SuccessResponse(message="Campaign created successfully", data=record)


@router.put("/campaigns/{campaign_id}", response_model=SuccessResponse)
def update_campaign(
    campaign_id: int,
    request: CampaignUpdateRequest,
    user_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
):
    record = OutreachService(db).update_campaign(campaign_id, request.model_dump(exclude_unset=True), user_id)
    return SuccessResponse(message="Campaign updated successfully", data=record)


@router.get("/campaigns/{campaign_id}/workflows", response_model=SuccessResponse)
def list_workflows(campaign_id: int, db: Session = Depends(get_db)):
    records = OutreachService(db).list_workflows(campaign_id)
    return SuccessResponse(message="Workflows retrieved successfully", data={"workflows": records, "count": len(records)})


@router.post("/campaigns/{campaign_id}/workflows", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
def create_workflow(campaign_id: int, request: WorkflowRequest, db: Session = Depends(get_db)):
    record = OutreachService(db).create_workflow(campaign_id, request.model_dump())
    return SuccessResponse(message="Workflow created successfully", data=record)


@router.put("/workflows/{workflow_id}", response_model=SuccessResponse)
def update_workflow(workflow_id: int, request: WorkflowUpdateRequest, db: Session = Depends(get_db)):
    record = OutreachService(db).update_workflow(workflow_id, request.model_dump(exclude_unset=True))
    return SuccessResponse(message="Workflow updated successfully", data=record)


@router.get("/checkin-templates", response_model=SuccessResponse)
def list_templates(organization_id: int | None = Query(default=None, gt=0), db: Session = Depends(get_db)):
    records = OutreachService(db).list_templates(organization_id)
    return SuccessResponse(message="Check-in templates retrieved successfully", data={"templates": records, "count": len(records)})


@router.post("/checkin-templates", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
def create_template(request: CheckinTemplateRequest, user_id: int = Query(..., gt=0), db: Session = Depends(get_db)):
    record = OutreachService(db).create_template(request.model_dump(), user_id)
    return SuccessResponse(message="Check-in template created successfully", data=record)


@router.get("/checkin-templates/{template_id}/questions", response_model=SuccessResponse)
def list_questions(template_id: int, db: Session = Depends(get_db)):
    records = OutreachService(db).list_questions(template_id)
    return SuccessResponse(message="Questions retrieved successfully", data={"questions": records, "count": len(records)})


@router.post("/checkin-templates/{template_id}/questions", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
def create_question(template_id: int, request: CheckinQuestionRequest, db: Session = Depends(get_db)):
    record = OutreachService(db).create_question(template_id, request.model_dump())
    return SuccessResponse(message="Question created successfully", data=record)


@router.get("/events", response_model=SuccessResponse)
def list_events(
    campaign_id: int | None = Query(default=None, gt=0),
    patient_id: int | None = Query(default=None, gt=0),
    event_status: str | None = None,
    db: Session = Depends(get_db),
):
    records = OutreachService(db).list_events(campaign_id, patient_id, event_status)
    return SuccessResponse(message="Outreach events retrieved successfully", data={"events": records, "count": len(records)})


@router.post("/events", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
def create_event(request: OutreachEventCreateRequest, db: Session = Depends(get_db)):
    record = OutreachService(db).create_event(request.model_dump())
    return SuccessResponse(message="Outreach event created successfully", data=record)


@router.put("/events/{event_id}", response_model=SuccessResponse)
def update_event(event_id: int, request: OutreachEventUpdateRequest, db: Session = Depends(get_db)):
    record = OutreachService(db).update_event(event_id, request.model_dump(exclude_unset=True))
    return SuccessResponse(message="Outreach event updated successfully", data=record)


@router.get("/checkin-sessions", response_model=SuccessResponse)
def list_sessions(patient_id: int | None = Query(default=None, gt=0), db: Session = Depends(get_db)):
    records = OutreachService(db).list_sessions(patient_id)
    return SuccessResponse(message="Check-in sessions retrieved successfully", data={"sessions": records, "count": len(records)})


@router.post("/checkin-sessions", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
def create_session(request: CheckinSessionRequest, db: Session = Depends(get_db)):
    record = OutreachService(db).create_session(request.model_dump())
    return SuccessResponse(message="Check-in session created successfully", data=record)


@router.post("/checkin-sessions/{session_id}/responses", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
def record_response(
    session_id: int,
    request: CheckinResponseRequest,
    user_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
):
    record = OutreachService(db).record_response(session_id, request.model_dump(), user_id)
    return SuccessResponse(message="Check-in response recorded successfully", data=record)


@router.get("/appointments/{appointment_id}/actions", response_model=SuccessResponse)
def list_appointment_actions(appointment_id: int, db: Session = Depends(get_db)):
    records = OutreachService(db).list_appointment_actions(appointment_id)
    return SuccessResponse(message="Appointment actions retrieved successfully", data={"actions": records, "count": len(records)})


@router.post("/appointments/{appointment_id}/actions", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
def create_appointment_action(
    appointment_id: int,
    request: AppointmentActionRequest,
    user_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
):
    record = OutreachService(db).create_appointment_action(appointment_id, request.model_dump(), user_id)
    return SuccessResponse(message="Appointment action recorded successfully", data=record)


@router.get("/follow-up-tasks", response_model=SuccessResponse)
def list_tasks(
    assigned_to_staff_id: int | None = Query(default=None, gt=0),
    task_status: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
):
    records = OutreachService(db).list_tasks(assigned_to_staff_id, task_status)
    return SuccessResponse(message="Follow-up tasks retrieved successfully", data={"tasks": records, "count": len(records)})


@router.post("/follow-up-tasks", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
def create_task(request: FollowUpTaskRequest, user_id: int = Query(..., gt=0), db: Session = Depends(get_db)):
    record = OutreachService(db).create_task(request.model_dump(), user_id)
    return SuccessResponse(message="Follow-up task created successfully", data=record)


@router.put("/follow-up-tasks/{task_id}", response_model=SuccessResponse)
def update_task(
    task_id: int,
    request: FollowUpTaskUpdateRequest,
    user_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
):
    record = OutreachService(db).update_task(task_id, request.model_dump(exclude_unset=True), user_id)
    return SuccessResponse(message="Follow-up task updated successfully", data=record)