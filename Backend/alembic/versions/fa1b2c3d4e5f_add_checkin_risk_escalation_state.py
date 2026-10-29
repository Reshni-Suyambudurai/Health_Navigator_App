"""Add deterministic check-in risk, escalation, expiry, and response state.

Revision ID: fa1b2c3d4e5f
Revises: f2a3b4c5d6e7, f6a7b8c9d0e1, f9a0b1c2d3e4
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "fa1b2c3d4e5f"
down_revision: Union[str, Sequence[str], None] = (
    "f2a3b4c5d6e7",
    "f6a7b8c9d0e1",
    "f9a0b1c2d3e4",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _create_enum(name: str, values: str) -> None:
    op.execute(
        f"DO $$ BEGIN CREATE TYPE {name} AS ENUM ({values}); "
        f"EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
    )


def _add_enum_value(name: str, value: str) -> None:
    op.execute(f"ALTER TYPE {name} ADD VALUE IF NOT EXISTS '{value}'")


def upgrade() -> None:
    _create_enum("checkin_risk_level", "'NORMAL', 'ROUTINE', 'EMERGENCY'")
    _create_enum("checkin_response_type", "'PATIENT_ANSWER', 'STAFF_RESPONSE'")
    _add_enum_value("checkin_session_status", "EXPIRED")

    op.add_column("checkin_templates", sa.Column("escalation_role_id", sa.BigInteger(), nullable=True))
    op.add_column("checkin_templates", sa.Column("expiry_after_hours", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_checkin_templates_escalation_role",
        "checkin_templates",
        "roles",
        ["escalation_role_id"],
        ["role_id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_checkin_templates_escalation_role_id", "checkin_templates", ["escalation_role_id"])

    op.add_column("checkin_questions", sa.Column("risk_level", sa.Enum(name="checkin_risk_level"), server_default="NORMAL", nullable=False))
    op.add_column("checkin_questions", sa.Column("critical_response", sa.JSON(), nullable=True))

    op.add_column("checkin_sessions", sa.Column("scheduled_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False))
    op.add_column("checkin_sessions", sa.Column("expires_at", sa.TIMESTAMP(), nullable=True))
    op.add_column("checkin_sessions", sa.Column("escalation_id", sa.BigInteger(), nullable=True))
    op.add_column("checkin_sessions", sa.Column("escalated_at", sa.TIMESTAMP(), nullable=True))
    op.add_column("checkin_sessions", sa.Column("escalation_reason", sa.Text(), nullable=True))
    op.add_column("checkin_sessions", sa.Column("staff_response_note", sa.Text(), nullable=True))
    op.add_column("checkin_sessions", sa.Column("staff_response_by_user_id", sa.BigInteger(), nullable=True))
    op.add_column("checkin_sessions", sa.Column("staff_responded_at", sa.TIMESTAMP(), nullable=True))
    op.create_foreign_key(
        "fk_checkin_sessions_escalation",
        "checkin_sessions",
        "escalations",
        ["escalation_id"],
        ["escalation_id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_checkin_sessions_staff_response_user",
        "checkin_sessions",
        "users",
        ["staff_response_by_user_id"],
        ["user_id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_checkin_sessions_escalation_id", "checkin_sessions", ["escalation_id"])

    op.add_column("checkin_responses", sa.Column("response_type", sa.Enum(name="checkin_response_type"), server_default="PATIENT_ANSWER", nullable=False))


def downgrade() -> None:
    op.drop_column("checkin_responses", "response_type")
    op.drop_index("ix_checkin_sessions_escalation_id", table_name="checkin_sessions")
    op.drop_constraint("fk_checkin_sessions_staff_response_user", "checkin_sessions", type_="foreignkey")
    op.drop_constraint("fk_checkin_sessions_escalation", "checkin_sessions", type_="foreignkey")
    for column in (
        "staff_responded_at",
        "staff_response_by_user_id",
        "staff_response_note",
        "escalation_reason",
        "escalated_at",
        "escalation_id",
        "expires_at",
        "scheduled_at",
    ):
        op.drop_column("checkin_sessions", column)
    op.drop_index("ix_checkin_templates_escalation_role_id", table_name="checkin_templates")
    op.drop_constraint("fk_checkin_templates_escalation_role", "checkin_templates", type_="foreignkey")
    op.drop_column("checkin_templates", "expiry_after_hours")
    op.drop_column("checkin_templates", "escalation_role_id")
    op.drop_column("checkin_questions", "critical_response")
    op.drop_column("checkin_questions", "risk_level")
    op.execute("DROP TYPE IF EXISTS checkin_response_type")
    op.execute("DROP TYPE IF EXISTS checkin_risk_level")
