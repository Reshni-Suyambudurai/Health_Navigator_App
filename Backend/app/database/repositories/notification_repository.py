"""Database operations for user notifications."""

from sqlalchemy.orm import Session

from app.database.models.notification import Notification, NotificationStatus
from app.database.models.role import Role, RoleName
from app.database.models.user import User, UserStatus


class NotificationRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_active_user(self, user_id: int) -> User | None:
        return (
            self.db.query(User)
            .filter(User.user_id == user_id, User.status == UserStatus.ACTIVE)
            .one_or_none()
        )

    def list_active_users_by_role(self, organization_id: int, role_name: RoleName) -> list[User]:
        return (
            self.db.query(User)
            .join(Role, Role.role_id == User.role_id)
            .filter(
                User.organization_id == organization_id,
                User.status == UserStatus.ACTIVE,
                Role.role_name == role_name,
            )
            .order_by(User.user_id.asc())
            .all()
        )

    def list_for_recipient(
        self,
        recipient_user_id: int,
        skip: int,
        limit: int,
    ) -> tuple[list[tuple[Notification, User]], int]:
        query = (
            self.db.query(Notification, User)
            .join(User, User.user_id == Notification.sender_user_id)
            .filter(Notification.recipient_user_id == recipient_user_id)
        )
        total = query.count()
        items = (
            query.order_by(Notification.created_at.desc(), Notification.notification_id.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return items, total

    def count_unread(self, recipient_user_id: int) -> int:
        return (
            self.db.query(Notification.notification_id)
            .filter(
                Notification.recipient_user_id == recipient_user_id,
                Notification.status == NotificationStatus.UNREAD,
            )
            .count()
        )

    def find_for_recipient(
        self,
        notification_id: int,
        recipient_user_id: int,
    ) -> tuple[Notification, User] | None:
        return (
            self.db.query(Notification, User)
            .join(User, User.user_id == Notification.sender_user_id)
            .filter(
                Notification.notification_id == notification_id,
                Notification.recipient_user_id == recipient_user_id,
            )
            .one_or_none()
        )

    def save(self, notification: Notification) -> Notification:
        try:
            self.db.add(notification)
            self.db.commit()
            self.db.refresh(notification)
            return notification
        except Exception:
            self.db.rollback()
            raise