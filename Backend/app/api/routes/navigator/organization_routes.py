"""System-admin organization HTTP endpoints."""

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.response_models import SuccessResponse
from app.database.connection import get_db
from app.services.navigator.organization_service import OrganizationService


router = APIRouter(prefix="/organizations", tags=["Organizations"])


class OrganizationUpdateRequest(BaseModel):
    organization_name: str | None = Field(default=None, min_length=1, max_length=255)
    organization_type: str | None = None
    npi_number: str | None = Field(default=None, max_length=20)
    address: str | None = Field(default=None, max_length=500)
    phone: str | None = Field(default=None, max_length=20)
    status: str | None = None
    contact_first_name: str | None = Field(default=None, min_length=1, max_length=100)
    contact_last_name: str | None = Field(default=None, min_length=1, max_length=100)
    contact_email: str | None = Field(default=None, min_length=3, max_length=255)
    contact_phone: str | None = Field(default=None, max_length=20)


@router.get("/current", response_model=SuccessResponse)
def get_current_organization(
    user_id: int = Query(..., gt=0, description="Authenticated system administrator user ID"),
    db: Session = Depends(get_db),
):
    organization = OrganizationService(db).get_current_organization(user_id)
    return SuccessResponse(
        status="success",
        message="Organization details retrieved successfully",
        data=organization,
    )


@router.put("/current", response_model=SuccessResponse)
def update_current_organization(
    request: Request,
    payload: OrganizationUpdateRequest,
    user_id: int = Query(..., gt=0, description="Authenticated system administrator user ID"),
    db: Session = Depends(get_db),
):
    organization = OrganizationService(db).update_current_organization(
        user_id=user_id,
        data=payload.model_dump(exclude_unset=True),
        ip_address=request.client.host if request.client else None,
        correlation_id=request.headers.get("X-Correlation-ID"),
    )
    return SuccessResponse(
        status="success",
        message="Organization details updated successfully",
        data=organization,
    )