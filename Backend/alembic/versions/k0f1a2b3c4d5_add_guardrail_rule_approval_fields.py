"""Add approval metadata to clinical guardrail rules.

Revision ID: k0f1a2b3c4d5
Revises: k0e1f2a3b4c5
Create Date: 2026-11-02 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "k0f1a2b3c4d5"
down_revision: Union[str, None] = "k0e1f2a3b4c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


approval_status = postgresql.ENUM(
    "DRAFT",
    "PENDING",
    "APPROVED",
    "REJECTED",
    name="guardrail_rule_approval_status",
    create_type=False,
)


def upgrade() -> None:
    approval_status.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "clinical_guardrail_rules",
        sa.Column("created_by_user_id", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "clinical_guardrail_rules",
        sa.Column(
            "approval_status",
            approval_status,
            server_default="DRAFT",
            nullable=False,
        ),
    )
    op.add_column(
        "clinical_guardrail_rules",
        sa.Column("approved_by_user_id", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "clinical_guardrail_rules",
        sa.Column("approved_at", sa.TIMESTAMP(), nullable=True),
    )
    op.add_column(
        "clinical_guardrail_rules",
        sa.Column("effective_from", sa.Date(), nullable=True),
    )
    op.add_column(
        "clinical_guardrail_rules",
        sa.Column("rejection_reason", sa.Text(), nullable=True),
    )

    op.create_foreign_key(
        "fk_clinical_guardrail_rules_created_by_user",
        "clinical_guardrail_rules",
        "users",
        ["created_by_user_id"],
        ["user_id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_clinical_guardrail_rules_approved_by_user",
        "clinical_guardrail_rules",
        "users",
        ["approved_by_user_id"],
        ["user_id"],
        ondelete="SET NULL",
    )

    op.create_index(
        "ix_clinical_guardrail_rules_created_by_user_id",
        "clinical_guardrail_rules",
        ["created_by_user_id"],
    )
    op.create_index(
        "ix_clinical_guardrail_rules_approval_status",
        "clinical_guardrail_rules",
        ["approval_status"],
    )
    op.create_index(
        "ix_clinical_guardrail_rules_approved_by_user_id",
        "clinical_guardrail_rules",
        ["approved_by_user_id"],
    )
    op.create_index(
        "ix_clinical_guardrail_rules_effective_from",
        "clinical_guardrail_rules",
        ["effective_from"],
    )

    op.execute(
        """
        UPDATE clinical_guardrail_rules
        SET approval_status = 'APPROVED',
            status = 'ACTIVE'
        """
    )


def downgrade() -> None:
    op.drop_index(
        "ix_clinical_guardrail_rules_effective_from",
        table_name="clinical_guardrail_rules",
    )
    op.drop_index(
        "ix_clinical_guardrail_rules_approved_by_user_id",
        table_name="clinical_guardrail_rules",
    )
    op.drop_index(
        "ix_clinical_guardrail_rules_approval_status",
        table_name="clinical_guardrail_rules",
    )
    op.drop_index(
        "ix_clinical_guardrail_rules_created_by_user_id",
        table_name="clinical_guardrail_rules",
    )

    op.drop_constraint(
        "fk_clinical_guardrail_rules_approved_by_user",
        "clinical_guardrail_rules",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_clinical_guardrail_rules_created_by_user",
        "clinical_guardrail_rules",
        type_="foreignkey",
    )

    op.drop_column("clinical_guardrail_rules", "rejection_reason")
    op.drop_column("clinical_guardrail_rules", "effective_from")
    op.drop_column("clinical_guardrail_rules", "approved_at")
    op.drop_column("clinical_guardrail_rules", "approved_by_user_id")
    op.drop_column("clinical_guardrail_rules", "approval_status")
    op.drop_column("clinical_guardrail_rules", "created_by_user_id")

    approval_status.drop(op.get_bind(), checkfirst=True)