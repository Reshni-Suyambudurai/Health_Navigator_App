"""User notification model."""

import enum

from sqlalchemy import BigInteger, Column, Enum as SQLEnum, ForeignKey, Identity, Index, String, Text, TIMESTAMP
from sqlalchemy.sql import func

from app.database.connection import Base


class NotificationType(enum.Enum):
    GENERAL = "GENERAL"
    ESCALATION = "ESCALATION"
    APPOINTMENT_REMINDER = "APPOINTMENT_REMINDER"
    OUTREACH_UPDATE = "OUTREACH_UPDATE"
    FOLLOW_UP = "FOLLOW_UP"
    SYSTEM_ALERT = "SYSTEM_ALERT"


class NotificationPriority(enum.Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"


class NotificationStatus(enum.Enum):
    UNREAD = "UNREAD"
    READ = "READ"
    ARCHIVED = "ARCHIVED"


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_recipient_status", "recipient_user_id", "status"),
        Index("ix_notifications_recipient_created", "recipient_user_id", "created_at"),
        Index("ix_notifications_sender_created", "sender_user_id", "created_at"),
    )

    notification_id = Column(BigInteger, Identity(), primary_key=True)
    organization_id = Column(
        BigInteger,
        ForeignKey("organizations.organization_id", ondelete="SET NULL"),
    )
    sender_user_id = Column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="RESTRICT"),
        nullable=False,
    )
    recipient_user_id = Column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="RESTRICT"),
        nullable=False,
    )
    title = Column(String(255))
    message = Column(Text, nullable=False)
    notification_type = Column(
        SQLEnum(NotificationType, name="notification_type"),
        nullable=False,
        server_default="GENERAL",
    )
    priority = Column(
        SQLEnum(NotificationPriority, name="notification_priority"),
        nullable=False,
        server_default="NORMAL",
    )
    status = Column(
        SQLEnum(NotificationStatus, name="notification_status"),
        nullable=False,
        server_default="UNREAD",
    )
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())
    read_at = Column(TIMESTAMP)