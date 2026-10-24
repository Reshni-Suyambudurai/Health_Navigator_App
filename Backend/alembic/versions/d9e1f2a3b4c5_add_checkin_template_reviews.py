"""Add check-in template clinical reviews.

Revision ID: d9e1f2a3b4c5
Revises: f5a6b7c8d9e0
"""

from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d9e1f2a3b4c5"
down_revision: Union[str, None] = "f5a6b7c8d9e0"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    review_status = postgresql.ENUM(
        "PENDING",
        "APPROVED",
        "REJECTED",
        name="checkin_template_review_status",
        create_type=False,
    )
    review_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "checkin_template_reviews",
        sa.Column("review_id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("checkin_template_id", sa.BigInteger(), nullable=False),
        sa.Column("submitted_by_user_id", sa.BigInteger(), nullable=False),
        sa.Column("reviewed_by_user_id", sa.BigInteger(), nullable=True),
        sa.Column("status", review_status, server_default="PENDING", nullable=False),
        sa.Column("submission_note", sa.String(length=1000), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("reviewed_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.ForeignKeyConstraint(["checkin_template_id"], ["checkin_templates.checkin_template_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["submitted_by_user_id"], ["users.user_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.user_id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("review_id"),
    )
    op.create_index("ix_checkin_template_reviews_checkin_template_id", "checkin_template_reviews", ["checkin_template_id"])
    op.create_index("ix_checkin_template_reviews_template_created", "checkin_template_reviews", ["checkin_template_id", "created_at"])
    op.create_index("ix_checkin_template_reviews_status", "checkin_template_reviews", ["status"])


def downgrade() -> None:
    op.drop_table("checkin_template_reviews")
    postgresql.ENUM(name="checkin_template_review_status").drop(op.get_bind(), checkfirst=True)