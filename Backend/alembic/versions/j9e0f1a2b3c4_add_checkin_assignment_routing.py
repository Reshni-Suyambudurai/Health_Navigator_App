"""Add check-in escalation assignment routing.

Revision ID: j9e0f1a2b3c4
Revises: i8d9e0f1a2b3
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "j9e0f1a2b3c4"
down_revision: Union[str, None] = "i8d9e0f1a2b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


assignment_status = sa.Enum(
    "ASSIGNED",
    "IN_PROGRESS",
    "COMPLETED",
    "CANCELLED",
    name="escalation_assignment_status",
)


def upgrade() -> None:
    assignment_status.create(op.get_bind(), checkfirst=True)

    op.add_column("care_team_queues", sa.Column("role_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        "fk_care_team_queues_role",
        "care_team_queues",
        "roles",
        ["role_id"],
        ["role_id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_care_team_queues_role_id", "care_team_queues", ["role_id"])
    op.create_unique_constraint(
        "uq_care_team_queues_org_role",
        "care_team_queues",
        ["organization_id", "role_id"],
    )

    op.add_column("checkin_escalations", sa.Column("target_role_id", sa.BigInteger(), nullable=True))
    op.add_column("checkin_escalations", sa.Column("queue_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        "fk_checkin_escalations_target_role",
        "checkin_escalations",
        "roles",
        ["target_role_id"],
        ["role_id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_checkin_escalations_queue",
        "checkin_escalations",
        "care_team_queues",
        ["queue_id"],
        ["queue_id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_checkin_escalations_target_role_id", "checkin_escalations", ["target_role_id"])
    op.create_index("ix_checkin_escalations_queue_id", "checkin_escalations", ["queue_id"])

    op.alter_column("escalation_assignments", "escalation_id", existing_type=sa.BigInteger(), nullable=True)
    op.add_column("escalation_assignments", sa.Column("checkin_escalation_id", sa.BigInteger(), nullable=True))
    op.add_column(
        "escalation_assignments",
        sa.Column(
            "assignment_status",
            assignment_status,
            nullable=False,
            server_default="ASSIGNED",
        ),
    )
    op.add_column("escalation_assignments", sa.Column("action_taken", sa.Text(), nullable=True))
    op.add_column("escalation_assignments", sa.Column("resolution_notes", sa.Text(), nullable=True))
    op.add_column("escalation_assignments", sa.Column("completed_at", sa.TIMESTAMP(), nullable=True))
    op.create_foreign_key(
        "fk_escalation_assignments_checkin",
        "escalation_assignments",
        "checkin_escalations",
        ["checkin_escalation_id"],
        ["checkin_escalation_id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_escalation_assignments_checkin_escalation_id",
        "escalation_assignments",
        ["checkin_escalation_id"],
    )
    op.create_index(
        "ix_escalation_assignments_assignment_status",
        "escalation_assignments",
        ["assignment_status"],
    )
    op.create_unique_constraint(
        "uq_escalation_assignments_checkin",
        "escalation_assignments",
        ["checkin_escalation_id"],
    )
    op.create_check_constraint(
        "chk_escalation_assignments_single_parent",
        "escalation_assignments",
        "(escalation_id IS NOT NULL) <> (checkin_escalation_id IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint("chk_escalation_assignments_single_parent", "escalation_assignments", type_="check")
    op.drop_constraint("uq_escalation_assignments_checkin", "escalation_assignments", type_="unique")
    op.drop_index("ix_escalation_assignments_assignment_status", table_name="escalation_assignments")
    op.drop_index("ix_escalation_assignments_checkin_escalation_id", table_name="escalation_assignments")
    op.drop_constraint("fk_escalation_assignments_checkin", "escalation_assignments", type_="foreignkey")
    op.drop_column("escalation_assignments", "completed_at")
    op.drop_column("escalation_assignments", "resolution_notes")
    op.drop_column("escalation_assignments", "action_taken")
    op.drop_column("escalation_assignments", "assignment_status")
    op.drop_column("escalation_assignments", "checkin_escalation_id")
    op.alter_column("escalation_assignments", "escalation_id", existing_type=sa.BigInteger(), nullable=False)

    op.drop_index("ix_checkin_escalations_queue_id", table_name="checkin_escalations")
    op.drop_index("ix_checkin_escalations_target_role_id", table_name="checkin_escalations")
    op.drop_constraint("fk_checkin_escalations_queue", "checkin_escalations", type_="foreignkey")
    op.drop_constraint("fk_checkin_escalations_target_role", "checkin_escalations", type_="foreignkey")
    op.drop_column("checkin_escalations", "queue_id")
    op.drop_column("checkin_escalations", "target_role_id")

    op.drop_constraint("uq_care_team_queues_org_role", "care_team_queues", type_="unique")
    op.drop_index("ix_care_team_queues_role_id", table_name="care_team_queues")
    op.drop_constraint("fk_care_team_queues_role", "care_team_queues", type_="foreignkey")
    op.drop_column("care_team_queues", "role_id")
    assignment_status.drop(op.get_bind(), checkfirst=True)