"""Authenticated user notification inbox routes."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.response_models import SuccessResponse
from app.database.connection import get_db
from app.schemas.notification import NotificationCreateRequest
from app.services.notification_service import NotificationService


router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.post("", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
def create_notification(
    payload: NotificationCreateRequest,
    user_id: int,
    db: Session = Depends(get_db),
):
    data = NotificationService(db).create_notification(
        sender_user_id=user_id,
        recipient_user_id=payload.recipient_user_id,
        title=payload.title,
        message=payload.message,
        notification_type=payload.notification_type,
        priority=payload.priority,
    )
    return SuccessResponse(message="Notification created successfully", data=data)


@router.get("", response_model=SuccessResponse)
def list_notifications(
    user_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    data = NotificationService(db).list_notifications(user_id, skip, limit)
    return SuccessResponse(message="Notifications retrieved successfully", data=data)


@router.get("/unread-count", response_model=SuccessResponse)
def unread_count(user_id: int, db: Session = Depends(get_db)):
    data = NotificationService(db).unread_count(user_id)
    return SuccessResponse(message="Unread notification count retrieved successfully", data=data)


@router.get("/{notification_id}", response_model=SuccessResponse)
def get_notification(notification_id: int, user_id: int, db: Session = Depends(get_db)):
    data = NotificationService(db).get_notification(user_id, notification_id)
    return SuccessResponse(message="Notification retrieved successfully", data=data)


@router.patch("/{notification_id}/read", response_model=SuccessResponse)
def mark_notification_read(notification_id: int, user_id: int, db: Session = Depends(get_db)):
    data = NotificationService(db).mark_read(user_id, notification_id)
    return SuccessResponse(message="Notification marked as read", data=data)