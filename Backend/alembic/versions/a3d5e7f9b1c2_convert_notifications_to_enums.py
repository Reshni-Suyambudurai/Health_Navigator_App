"""Convert notification classifications to PostgreSQL enums.

Revision ID: a3d5e7f9b1c2
Revises: e2c4a6b8d0f1
"""

from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "a3d5e7f9b1c2"
down_revision: Union[str, None] = "e2c4a6b8d0f1"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


notification_type = postgresql.ENUM(
    "GENERAL",
    "ESCALATION",
    "APPOINTMENT_REMINDER",
    "OUTREACH_UPDATE",
    "FOLLOW_UP",
    "SYSTEM_ALERT",
    name="notification_type",
    create_type=False,
)
notification_priority = postgresql.ENUM(
    "LOW",
    "NORMAL",
    "HIGH",
    "URGENT",
    name="notification_priority",
    create_type=False,
)
notification_status = postgresql.ENUM(
    "UNREAD",
    "READ",
    "ARCHIVED",
    name="notification_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    notification_type.create(bind, checkfirst=True)
    notification_priority.create(bind, checkfirst=True)
    notification_status.create(bind, checkfirst=True)

    op.drop_constraint("chk_notifications_type", "notifications", type_="check")
    op.drop_constraint("chk_notifications_priority", "notifications", type_="check")
    op.drop_constraint("chk_notifications_status", "notifications", type_="check")

    op.alter_column("notifications", "notification_type", server_default=None)
    op.alter_column("notifications", "priority", server_default=None)
    op.alter_column("notifications", "status", server_default=None)
    op.alter_column(
        "notifications",
        "notification_type",
        existing_type=sa.String(length=50),
        type_=notification_type,
        postgresql_using="notification_type::text::notification_type",
        existing_nullable=False,
    )
    op.alter_column(
        "notifications",
        "priority",
        existing_type=sa.String(length=20),
        type_=notification_priority,
        postgresql_using="priority::text::notification_priority",
        existing_nullable=False,
    )
    op.alter_column(
        "notifications",
        "status",
        existing_type=sa.String(length=20),
        type_=notification_status,
        postgresql_using="status::text::notification_status",
        existing_nullable=False,
    )
    op.alter_column("notifications", "notification_type", server_default="GENERAL")
    op.alter_column("notifications", "priority", server_default="NORMAL")
    op.alter_column("notifications", "status", server_default="UNREAD")


def downgrade() -> None:
    op.alter_column("notifications", "notification_type", server_default=None)
    op.alter_column("notifications", "priority", server_default=None)
    op.alter_column("notifications", "status", server_default=None)
    op.alter_column(
        "notifications",
        "notification_type",
        existing_type=notification_type,
        type_=sa.String(length=50),
        postgresql_using="notification_type::text",
        existing_nullable=False,
    )
    op.alter_column(
        "notifications",
        "priority",
        existing_type=notification_priority,
        type_=sa.String(length=20),
        postgresql_using="priority::text",
        existing_nullable=False,
    )
    op.alter_column(
        "notifications",
        "status",
        existing_type=notification_status,
        type_=sa.String(length=20),
        postgresql_using="status::text",
        existing_nullable=False,
    )
    op.alter_column("notifications", "notification_type", server_default="GENERAL")
    op.alter_column("notifications", "priority", server_default="NORMAL")
    op.alter_column("notifications", "status", server_default="UNREAD")

    op.create_check_constraint(
        "chk_notifications_type",
        "notifications",
        "notification_type IN ('GENERAL', 'ESCALATION', 'APPOINTMENT_REMINDER', "
        "'OUTREACH_UPDATE', 'FOLLOW_UP', 'SYSTEM_ALERT')",
    )
    op.create_check_constraint(
        "chk_notifications_priority",
        "notifications",
        "priority IN ('LOW', 'NORMAL', 'HIGH', 'URGENT')",
    )
    op.create_check_constraint(
        "chk_notifications_status",
        "notifications",
        "status IN ('UNREAD', 'READ', 'ARCHIVED')",
    )

    notification_status.drop(op.get_bind(), checkfirst=True)
    notification_priority.drop(op.get_bind(), checkfirst=True)
    notification_type.drop(op.get_bind(), checkfirst=True)