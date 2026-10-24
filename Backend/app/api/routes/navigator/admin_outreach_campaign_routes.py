"""System Admin outreach campaign configuration routes."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.response_models import SuccessResponse
from app.database.connection import get_db
from app.schemas.admin_outreach_campaign import (
    AdminCampaignCreateRequest,
    AdminCampaignStatusRequest,
    AdminCampaignUpdateRequest,
    AdminWorkflowRequest,
    AdminWorkflowUpdateRequest,
)
from app.services.navigator.admin_outreach_campaign_service import AdminOutreachCampaignService


router = APIRouter(prefix="/admin/outreach-campaigns", tags=["System Admin Outreach Campaigns"])


@router.get("", response_model=SuccessResponse)
def list_campaigns(
    user_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=25, ge=1, le=100),
    campaign_status: str | None = None,
    campaign_type: str | None = None,
    db: Session = Depends(get_db),
):
    data = AdminOutreachCampaignService(db).list_campaigns(
        user_id, skip, limit, campaign_status, campaign_type
    )
    return SuccessResponse(message="Campaigns retrieved successfully", data=data)


@router.get("/templates", response_model=SuccessResponse)
def list_templates(user_id: int, db: Session = Depends(get_db)):
    templates = AdminOutreachCampaignService(db).list_templates(user_id)
    return SuccessResponse(message="Active check-in templates retrieved successfully", data={"templates": templates})


@router.post("", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
def create_campaign(
    payload: AdminCampaignCreateRequest,
    user_id: int,
    db: Session = Depends(get_db),
):
    data = AdminOutreachCampaignService(db).create_campaign(user_id, payload.model_dump())
    return SuccessResponse(message="Campaign saved as draft", data=data)


@router.get("/{campaign_id}", response_model=SuccessResponse)
def get_campaign(campaign_id: int, user_id: int, db: Session = Depends(get_db)):
    data = AdminOutreachCampaignService(db).get_campaign(user_id, campaign_id)
    return SuccessResponse(message="Campaign retrieved successfully", data=data)


@router.put("/{campaign_id}", response_model=SuccessResponse)
def update_campaign(
    campaign_id: int,
    payload: AdminCampaignUpdateRequest,
    user_id: int,
    db: Session = Depends(get_db),
):
    data = AdminOutreachCampaignService(db).update_campaign(
        user_id, campaign_id, payload.model_dump(exclude_unset=True)
    )
    return SuccessResponse(message="Campaign updated successfully", data=data)


@router.get("/{campaign_id}/cohort-preview", response_model=SuccessResponse)
def preview_cohort(campaign_id: int, user_id: int, db: Session = Depends(get_db)):
    data = AdminOutreachCampaignService(db).preview_cohort(user_id, campaign_id)
    return SuccessResponse(message="Eligible cohort evaluated successfully", data=data)


@router.get("/{campaign_id}/cohort-members", response_model=SuccessResponse)
def list_cohort_members(
    campaign_id: int,
    user_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    data = AdminOutreachCampaignService(db).list_cohort_members(
        user_id,
        campaign_id,
        skip,
        limit,
    )
    return SuccessResponse(message="Eligible cohort patients retrieved successfully", data=data)


@router.patch("/{campaign_id}/status", response_model=SuccessResponse)
def transition_campaign_status(
    campaign_id: int,
    payload: AdminCampaignStatusRequest,
    user_id: int,
    db: Session = Depends(get_db),
):
    data = AdminOutreachCampaignService(db).transition_status(user_id, campaign_id, payload.status)
    return SuccessResponse(message=f"Campaign status changed to {payload.status}", data=data)


@router.get("/{campaign_id}/workflows", response_model=SuccessResponse)
def list_workflows(campaign_id: int, user_id: int, db: Session = Depends(get_db)):
    data = AdminOutreachCampaignService(db).list_workflows(user_id, campaign_id)
    return SuccessResponse(message="Campaign workflows retrieved successfully", data=data)


@router.post("/{campaign_id}/workflows", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
def create_workflow(
    campaign_id: int,
    payload: AdminWorkflowRequest,
    user_id: int,
    db: Session = Depends(get_db),
):
    data = AdminOutreachCampaignService(db).create_workflow(
        user_id, campaign_id, payload.model_dump()
    )
    return SuccessResponse(message="Workflow created successfully", data=data)


@router.put("/workflows/{workflow_id}", response_model=SuccessResponse)
def update_workflow(
    workflow_id: int,
    payload: AdminWorkflowUpdateRequest,
    user_id: int,
    db: Session = Depends(get_db),
):
    data = AdminOutreachCampaignService(db).update_workflow(
        user_id, workflow_id, payload.model_dump(exclude_unset=True)
    )
    return SuccessResponse(message="Workflow updated successfully", data=data)