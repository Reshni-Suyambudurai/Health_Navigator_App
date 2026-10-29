"""Add question-level escalation destination."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "fb2c3d4e5f6a"
down_revision: Union[str, None] = "fa1b2c3d4e5f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("checkin_questions", sa.Column("escalation_role_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        "fk_checkin_questions_escalation_role",
        "checkin_questions",
        "roles",
        ["escalation_role_id"],
        ["role_id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_checkin_questions_escalation_role_id", "checkin_questions", ["escalation_role_id"])


def downgrade() -> None:
    op.drop_index("ix_checkin_questions_escalation_role_id", table_name="checkin_questions")
    op.drop_constraint("fk_checkin_questions_escalation_role", "checkin_questions", type_="foreignkey")
    op.drop_column("checkin_questions", "escalation_role_id")
