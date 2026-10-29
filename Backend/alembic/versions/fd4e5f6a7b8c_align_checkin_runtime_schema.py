"""Align check-in runtime tables with the dedicated escalation schema."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "fd4e5f6a7b8c"
down_revision: Union[str, None] = "fc3d4e5f6a7b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE checkin_session_status ADD VALUE IF NOT EXISTS 'OVERDUE'")

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
    ):
        op.drop_column("checkin_sessions", column)

    op.create_index(
        "ix_checkin_sessions_scheduled_status",
        "checkin_sessions",
        ["scheduled_at", "session_status"],
    )
    op.create_index("ix_checkin_sessions_expires_at", "checkin_sessions", ["expires_at"])

    op.drop_column("checkin_responses", "response_type")
    op.execute("DROP TYPE IF EXISTS checkin_response_type")
    op.add_column(
        "checkin_responses",
        sa.Column(
            "evaluated_risk_level",
            postgresql.ENUM("NORMAL", "ROUTINE", "EMERGENCY", name="checkin_risk_level", create_type=False),
            server_default="NORMAL",
            nullable=False,
        ),
    )
    op.add_column("checkin_responses", sa.Column("risk_evaluation", sa.JSON(), nullable=True))
    op.create_index(
        "ix_checkin_responses_risk_answered",
        "checkin_responses",
        ["evaluated_risk_level", "answered_at"],
    )

    op.execute(
        """DO $$ BEGIN
        CREATE TYPE checkin_escalation_type AS ENUM ('EMERGENCY', 'SAME_DAY', 'ROUTINE');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;"""
    )
    op.execute(
        """DO $$ BEGIN
        CREATE TYPE checkin_escalation_status AS ENUM ('OPEN', 'ASSIGNED', 'IN_PROGRESS', 'RESOLVED', 'CANCELLED');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;"""
    )
    op.create_table(
        "checkin_escalations",
        sa.Column("checkin_escalation_id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("checkin_session_id", sa.BigInteger(), nullable=False),
        sa.Column("response_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "escalation_type",
            postgresql.ENUM(
                "EMERGENCY",
                "SAME_DAY",
                "ROUTINE",
                name="checkin_escalation_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("escalation_reason", sa.Text(), nullable=False),
        sa.Column("trigger_source", sa.String(length=30), nullable=True),
        sa.Column("matched_rule_key", sa.String(length=100), nullable=True),
        sa.Column(
            "escalation_status",
            postgresql.ENUM(
                "OPEN",
                "ASSIGNED",
                "IN_PROGRESS",
                "RESOLVED",
                "CANCELLED",
                name="checkin_escalation_status",
                create_type=False,
            ),
            server_default="OPEN",
            nullable=False,
        ),
        sa.Column("assigned_to_staff_id", sa.BigInteger(), nullable=True),
        sa.Column("assigned_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("resolved_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("action_taken", sa.Text(), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.ForeignKeyConstraint(
            ["checkin_session_id"],
            ["checkin_sessions.checkin_session_id"],
            name="fk_checkin_escalations_session",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["response_id"],
            ["checkin_responses.response_id"],
            name="fk_checkin_escalations_response",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["assigned_to_staff_id"],
            ["staff_profiles.staff_id"],
            name="fk_checkin_escalations_staff",
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_checkin_escalations_session", "checkin_escalations", ["checkin_session_id"])
    op.create_index("ix_checkin_escalations_response", "checkin_escalations", ["response_id"])


def downgrade() -> None:
    op.drop_index("ix_checkin_escalations_response", table_name="checkin_escalations")
    op.drop_index("ix_checkin_escalations_session", table_name="checkin_escalations")
    op.drop_table("checkin_escalations")
    op.execute("DROP TYPE IF EXISTS checkin_escalation_status")
    op.execute("DROP TYPE IF EXISTS checkin_escalation_type")

    op.drop_index("ix_checkin_responses_risk_answered", table_name="checkin_responses")
    op.drop_column("checkin_responses", "risk_evaluation")
    op.drop_column("checkin_responses", "evaluated_risk_level")
    op.execute("CREATE TYPE checkin_response_type AS ENUM ('PATIENT_ANSWER', 'STAFF_RESPONSE')")
    op.add_column(
        "checkin_responses",
        sa.Column("response_type", sa.Enum(name="checkin_response_type"), server_default="PATIENT_ANSWER", nullable=False),
    )

    op.drop_index("ix_checkin_sessions_expires_at", table_name="checkin_sessions")
    op.drop_index("ix_checkin_sessions_scheduled_status", table_name="checkin_sessions")
    for column in (
        "escalation_id",
        "escalated_at",
        "escalation_reason",
        "staff_response_note",
        "staff_response_by_user_id",
        "staff_responded_at",
    ):
        if column == "escalation_id":
            op.add_column("checkin_sessions", sa.Column(column, sa.BigInteger(), nullable=True))
        elif column == "staff_response_by_user_id":
            op.add_column("checkin_sessions", sa.Column(column, sa.BigInteger(), nullable=True))
        else:
            op.add_column("checkin_sessions", sa.Column(column, sa.TIMESTAMP() if column.endswith("at") else sa.Text(), nullable=True))
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
