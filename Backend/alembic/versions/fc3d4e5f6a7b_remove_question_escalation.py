"""Remove unsupported question-level escalation destination."""

from typing import Sequence, Union

from alembic import op


revision: str = "fc3d4e5f6a7b"
down_revision: Union[str, None] = "fb2c3d4e5f6a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_checkin_questions_escalation_role_id", table_name="checkin_questions")
    op.drop_constraint("fk_checkin_questions_escalation_role", "checkin_questions", type_="foreignkey")
    op.drop_column("checkin_questions", "escalation_role_id")


def downgrade() -> None:
    import sqlalchemy as sa

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
