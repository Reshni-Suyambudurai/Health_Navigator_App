"""Reusable notification creation and recipient inbox business logic."""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AuthorizationException, ConflictException, NotFoundException, ValidationException
from app.database.models.notification import (
    Notification,
    NotificationPriority,
    NotificationStatus,
    NotificationType,
)
from app.database.models.role import RoleName
from app.database.repositories.notification_repository import NotificationRepository


class NotificationService:
    def __init__(self, db: Session):
        self.repository = NotificationRepository(db)

    def create_notification(
        self,
        sender_user_id: int,
        recipient_user_id: int,
        message: str,
        title: str | None = None,
        notification_type: NotificationType | str = NotificationType.GENERAL,
        priority: NotificationPriority | str = NotificationPriority.NORMAL,
    ) -> dict[str, Any]:
        sender = self._require_active_user(sender_user_id)
        recipient = self._require_active_user(recipient_user_id)
        notification = self._build_notification(
            sender,
            recipient,
            message,
            title,
            notification_type,
            priority,
        )
        try:
            self.repository.save(notification)
        except SQLAlchemyError as exc:
            raise ConflictException("Notification could not be saved", "NOTIFICATION_SAVE_FAILED") from exc
        return self._serialize(notification, sender)

    def prepare_for_role(
        self,
        sender_user_id: int,
        organization_id: int,
        role_name: RoleName,
        message: str,
        title: str | None = None,
        notification_type: NotificationType | str = NotificationType.GENERAL,
        priority: NotificationPriority | str = NotificationPriority.NORMAL,
    ) -> list[Notification]:
        sender = self._require_active_user(sender_user_id)
        if sender.organization_id != organization_id:
            raise AuthorizationException("Notification organization does not match the sender")
        recipients = self.repository.list_active_users_by_role(organization_id, role_name)
        return [
            self._build_notification(
                sender,
                recipient,
                message,
                title,
                notification_type,
                priority,
            )
            for recipient in recipients
        ]

    def list_notifications(
        self,
        actor_user_id: int,
        skip: int = 0,
        limit: int = 50,
    ) -> dict[str, Any]:
        recipient = self._require_active_user(actor_user_id)
        items, total = self.repository.list_for_recipient(recipient.user_id, skip, limit)
        return {
            "notifications": [self._serialize(notification, sender) for notification, sender in items],
            "count": total,
            "unread_count": self.repository.count_unread(recipient.user_id),
        }

    def unread_count(self, actor_user_id: int) -> dict[str, int]:
        recipient = self._require_active_user(actor_user_id)
        return {"unread_count": self.repository.count_unread(recipient.user_id)}

    def get_notification(self, actor_user_id: int, notification_id: int) -> dict[str, Any]:
        recipient = self._require_active_user(actor_user_id)
        notification, sender = self._require_notification(notification_id, recipient.user_id)
        return self._serialize(notification, sender)

    def mark_read(self, actor_user_id: int, notification_id: int) -> dict[str, Any]:
        recipient = self._require_active_user(actor_user_id)
        notification, sender = self._require_notification(notification_id, recipient.user_id)
        if notification.status == NotificationStatus.UNREAD:
            notification.status = NotificationStatus.READ
            notification.read_at = datetime.now(timezone.utc).replace(tzinfo=None)
            try:
                self.repository.save(notification)
            except SQLAlchemyError as exc:
                raise ConflictException("Notification could not be marked as read", "NOTIFICATION_READ_FAILED") from exc
        return self._serialize(notification, sender)

    def _require_active_user(self, user_id: int):
        user = self.repository.find_active_user(user_id)
        if user is None:
            raise AuthorizationException("An active user account is required")
        return user

    def _require_notification(self, notification_id: int, recipient_user_id: int):
        result = self.repository.find_for_recipient(notification_id, recipient_user_id)
        if result is None:
            raise NotFoundException("Notification not found", "NOTIFICATION_NOT_FOUND")
        return result

    def _build_notification(
        self,
        sender,
        recipient,
        message: str,
        title: str | None,
        notification_type: NotificationType | str,
        priority: NotificationPriority | str,
    ) -> Notification:
        if sender.organization_id != recipient.organization_id:
            raise AuthorizationException("Notifications cannot be sent across organizations")
        return Notification(
            organization_id=sender.organization_id,
            sender_user_id=sender.user_id,
            recipient_user_id=recipient.user_id,
            title=self._optional_text(title),
            message=self._required_text(message, "Notification message"),
            notification_type=self._enum(NotificationType, notification_type, "notification type"),
            priority=self._enum(NotificationPriority, priority, "notification priority"),
            status=NotificationStatus.UNREAD,
        )

    @staticmethod
    def _enum(enum_type, value, label: str):
        if isinstance(value, enum_type):
            return value
        try:
            return enum_type(value)
        except ValueError as exc:
            raise ValidationException(f"Invalid {label}") from exc

    @staticmethod
    def _required_text(value: Any, label: str) -> str:
        text = str(value).strip() if value is not None else ""
        if not text:
            raise ValidationException(f"{label} is required")
        return text

    @staticmethod
    def _optional_text(value: Any) -> str | None:
        if value is None:
            return None
        return str(value).strip() or None

    @staticmethod
    def _serialize(notification: Notification, sender) -> dict[str, Any]:
        return {
            "notification_id": notification.notification_id,
            "organization_id": notification.organization_id,
            "sender_user_id": notification.sender_user_id,
            "sender_name": f"{sender.first_name} {sender.last_name}",
            "recipient_user_id": notification.recipient_user_id,
            "title": notification.title,
            "message": notification.message,
            "notification_type": notification.notification_type.value,
            "priority": notification.priority.value,
            "status": notification.status.value,
            "created_at": notification.created_at.isoformat() if notification.created_at else None,
            "read_at": notification.read_at.isoformat() if notification.read_at else None,
        }