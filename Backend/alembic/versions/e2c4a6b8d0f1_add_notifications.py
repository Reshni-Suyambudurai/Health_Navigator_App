"""Add user notifications.

Revision ID: e2c4a6b8d0f1
Revises: d9e1f2a3b4c5
"""

from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "e2c4a6b8d0f1"
down_revision: Union[str, None] = "d9e1f2a3b4c5"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("notification_id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("organization_id", sa.BigInteger(), nullable=True),
        sa.Column("sender_user_id", sa.BigInteger(), nullable=False),
        sa.Column("recipient_user_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("notification_type", sa.String(length=50), server_default="GENERAL", nullable=False),
        sa.Column("priority", sa.String(length=20), server_default="NORMAL", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="UNREAD", nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("read_at", sa.TIMESTAMP(), nullable=True),
        sa.CheckConstraint(
            "notification_type IN ('GENERAL', 'ESCALATION', 'APPOINTMENT_REMINDER', "
            "'OUTREACH_UPDATE', 'FOLLOW_UP', 'SYSTEM_ALERT')",
            name="chk_notifications_type",
        ),
        sa.CheckConstraint(
            "priority IN ('LOW', 'NORMAL', 'HIGH', 'URGENT')",
            name="chk_notifications_priority",
        ),
        sa.CheckConstraint(
            "status IN ('UNREAD', 'READ', 'ARCHIVED')",
            name="chk_notifications_status",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.organization_id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["sender_user_id"],
            ["users.user_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["recipient_user_id"],
            ["users.user_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("notification_id"),
    )
    op.create_index(
        "ix_notifications_recipient_status",
        "notifications",
        ["recipient_user_id", "status"],
    )
    op.create_index(
        "ix_notifications_recipient_created",
        "notifications",
        ["recipient_user_id", "created_at"],
    )
    op.create_index(
        "ix_notifications_sender_created",
        "notifications",
        ["sender_user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("notifications")