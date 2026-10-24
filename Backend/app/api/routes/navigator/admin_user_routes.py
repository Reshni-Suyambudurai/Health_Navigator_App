"""System-admin user management and audit-trail routes."""

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.core.response_models import SuccessResponse
from app.database.connection import get_db
from app.schemas.admin_user import AdminUserCreateRequest, AdminUserStatusRequest, AdminUserUpdateRequest
from app.services.navigator.admin_user_service import AdminUserService


router = APIRouter(prefix="/admin", tags=["System Admin"])


@router.get("/users", response_model=SuccessResponse)
def list_admin_users(
    user_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=25, ge=1, le=100),
    search: str | None = None,
    role_name: str | None = None,
    user_status: str | None = None,
    db: Session = Depends(get_db),
):
    data = AdminUserService(db).list_users(user_id, skip, limit, search, role_name, user_status)
    return SuccessResponse(status="success", message="Users retrieved successfully", data=data)


@router.get("/roles", response_model=SuccessResponse)
def list_assignable_roles(user_id: int, db: Session = Depends(get_db)):
    roles = AdminUserService(db).list_roles(user_id)
    return SuccessResponse(status="success", message="Assignable roles retrieved successfully", data={"roles": roles})


@router.post("/users", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
def create_admin_user(
    payload: AdminUserCreateRequest,
    request: Request,
    user_id: int,
    db: Session = Depends(get_db),
):
    user = AdminUserService(db).create_user(
        user_id,
        payload.model_dump(),
        request.client.host if request.client else None,
        request.headers.get("X-Correlation-ID"),
    )
    return SuccessResponse(status="success", message="User account created successfully", data=user)


@router.put("/users/{target_user_id}", response_model=SuccessResponse)
def update_admin_user(
    target_user_id: int,
    payload: AdminUserUpdateRequest,
    request: Request,
    user_id: int,
    db: Session = Depends(get_db),
):
    user = AdminUserService(db).update_user(
        user_id,
        target_user_id,
        payload.model_dump(exclude_unset=True),
        request.client.host if request.client else None,
        request.headers.get("X-Correlation-ID"),
    )
    return SuccessResponse(status="success", message="User account updated successfully", data=user)


@router.patch("/users/{target_user_id}/status", response_model=SuccessResponse)
def update_admin_user_status(
    target_user_id: int,
    payload: AdminUserStatusRequest,
    request: Request,
    user_id: int,
    db: Session = Depends(get_db),
):
    user = AdminUserService(db).update_status(
        user_id,
        target_user_id,
        payload.status,
        request.client.host if request.client else None,
        request.headers.get("X-Correlation-ID"),
    )
    return SuccessResponse(status="success", message="User account status updated successfully", data=user)


@router.get("/audit-trail", response_model=SuccessResponse)
def list_admin_audit_trail(
    user_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=25, ge=1, le=100),
    action: str | None = None,
    db: Session = Depends(get_db),
):
    data = AdminUserService(db).list_audit_trail(user_id, skip, limit, action)
    return SuccessResponse(status="success", message="Audit trail retrieved successfully", data=data)