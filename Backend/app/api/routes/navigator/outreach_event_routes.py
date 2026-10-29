"""Protected read-only outreach event routes."""

from datetime import datetime
import logging

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.core.response_models import SuccessResponse
from app.database.connection import get_db
from app.database.models.role import RoleName
from app.services.navigator.outreach_event_access_service import OutreachEventAccessService


router = APIRouter(tags=["Outreach Event Access"])
logger = logging.getLogger(__name__)


def _list(
    actor_user_id: int,
    role: RoleName,
    organization_id: int,
    campaign_id: list[int] | None,
    workflow_id: list[int] | None,
    campaign_name: str | None,
    workflow_name: str | None,
    event_status: list[str] | None,
    delivery_status: list[str] | None,
    scheduled_from: datetime | None,
    scheduled_to: datetime | None,
    patient_search: str | None,
    patient_id: list[int] | None,
    skip: int,
    limit: int,
    db: Session,
):
    data = OutreachEventAccessService(db).list_events(
        actor_user_id,
        role,
        organization_id=organization_id,
        campaign_id=campaign_id,
        workflow_id=workflow_id,
        campaign_name=campaign_name,
        workflow_name=workflow_name,
        event_status=event_status,
        delivery_status=delivery_status,
        scheduled_from=scheduled_from,
        scheduled_to=scheduled_to,
        patient_search=patient_search,
        patient_id=patient_id,
        skip=skip,
        limit=limit,
    )
    return SuccessResponse(message="Outreach events retrieved successfully", data=data)


def _filter_options(
    actor_user_id: int,
    role: RoleName,
    organization_id: int | None,
    campaign_id: int | None,
    db: Session,
):
    data = OutreachEventAccessService(db).list_filter_options(
        actor_user_id,
        role,
        organization_id=organization_id,
        campaign_id=campaign_id,
    )
    return SuccessResponse(message="Outreach event filters retrieved successfully", data=data)


def _detail(event_id: int, actor_user_id: int, role: RoleName, db: Session, request: Request):
    try:
        data = OutreachEventAccessService(db).get_event(
            actor_user_id,
            role,
            event_id,
            ip_address=request.client.host if request.client else None,
            correlation_id=request.headers.get("X-Correlation-ID"),
        )
        return SuccessResponse(message="Outreach event retrieved successfully", data=data)
    except Exception:
        logger.exception(
            "Outreach event detail failed: event_id=%s actor_user_id=%s role=%s",
            event_id,
            actor_user_id,
            role.value,
        )
        raise


@router.get("/admin/outreach-events", response_model=SuccessResponse)
def list_admin_events(
    actor_user_id: int = Query(..., alias="user_id", gt=0),
    organization_id: int = Query(..., gt=0),
    campaign_id: list[int] | None = Query(default=None),
    workflow_id: list[int] | None = Query(default=None),
    campaign_name: str | None = None,
    workflow_name: str | None = None,
    event_status: list[str] | None = Query(default=None),
    delivery_status: list[str] | None = Query(default=None),
    scheduled_from: datetime | None = None,
    scheduled_to: datetime | None = None,
    patient_search: str | None = None,
    patient_id: list[int] | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return _list(actor_user_id, RoleName.SYSTEM_ADMIN, organization_id, campaign_id, workflow_id, campaign_name, workflow_name, event_status, delivery_status, scheduled_from, scheduled_to, patient_search, patient_id, skip, limit, db)


@router.get("/admin/outreach-events/options", response_model=SuccessResponse)
def list_admin_event_options(
    actor_user_id: int = Query(..., alias="user_id", gt=0),
    organization_id: int = Query(..., gt=0),
    campaign_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
):
    return _filter_options(actor_user_id, RoleName.SYSTEM_ADMIN, organization_id, campaign_id, db)


@router.get("/admin/outreach-events/{event_id}", response_model=SuccessResponse)
def get_admin_event(
    event_id: int,
    request: Request,
    actor_user_id: int = Query(..., alias="user_id", gt=0),
    db: Session = Depends(get_db),
):
    return _detail(event_id, actor_user_id, RoleName.SYSTEM_ADMIN, db, request)


@router.get("/care-manager/outreach-events", response_model=SuccessResponse)
def list_care_manager_events(
    actor_user_id: int = Query(..., alias="user_id", gt=0),
    organization_id: int = Query(..., gt=0),
    campaign_id: list[int] | None = Query(default=None),
    workflow_id: list[int] | None = Query(default=None),
    campaign_name: str | None = None,
    workflow_name: str | None = None,
    event_status: list[str] | None = Query(default=None),
    delivery_status: list[str] | None = Query(default=None),
    scheduled_from: datetime | None = None,
    scheduled_to: datetime | None = None,
    patient_search: str | None = None,
    patient_id: list[int] | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return _list(actor_user_id, RoleName.CARE_MANAGER, organization_id, campaign_id, workflow_id, campaign_name, workflow_name, event_status, delivery_status, scheduled_from, scheduled_to, patient_search, patient_id, skip, limit, db)


@router.get("/care-manager/outreach-events/options", response_model=SuccessResponse)
def list_care_manager_event_options(
    actor_user_id: int = Query(..., alias="user_id", gt=0),
    organization_id: int = Query(..., gt=0),
    campaign_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
):
    return _filter_options(actor_user_id, RoleName.CARE_MANAGER, organization_id, campaign_id, db)


@router.get("/care-manager/outreach-events/{event_id}", response_model=SuccessResponse)
def get_care_manager_event(
    event_id: int,
    request: Request,
    actor_user_id: int = Query(..., alias="user_id", gt=0),
    db: Session = Depends(get_db),
):
    return _detail(event_id, actor_user_id, RoleName.CARE_MANAGER, db, request)
