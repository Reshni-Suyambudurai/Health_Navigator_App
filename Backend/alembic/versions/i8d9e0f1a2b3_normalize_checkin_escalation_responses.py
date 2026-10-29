"""Normalize check-in escalation response links.

Revision ID: i8d9e0f1a2b3
Revises: h7c8d9e0f1a2
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "i8d9e0f1a2b3"
down_revision: Union[str, None] = "h7c8d9e0f1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "checkin_escalation_responses",
        sa.Column("checkin_escalation_id", sa.BigInteger(), nullable=False),
        sa.Column("response_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(
            ["checkin_escalation_id"],
            ["checkin_escalations.checkin_escalation_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["response_id"],
            ["checkin_responses.response_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("checkin_escalation_id", "response_id"),
    )

    op.execute(
        """
        INSERT INTO checkin_escalation_responses (checkin_escalation_id, response_id)
        SELECT checkin_escalation_id, response_id
        FROM checkin_escalations
        ON CONFLICT DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO checkin_escalation_responses (checkin_escalation_id, response_id)
        SELECT canonical.checkin_escalation_id, escalation.response_id
        FROM checkin_escalations escalation
        JOIN (
            SELECT checkin_session_id, MIN(checkin_escalation_id) AS checkin_escalation_id
            FROM checkin_escalations
            GROUP BY checkin_session_id
        ) canonical USING (checkin_session_id)
        ON CONFLICT DO NOTHING
        """
    )
    op.execute(
        """
        UPDATE checkin_escalations retained
        SET escalation_type = severity.escalation_type::checkin_escalation_type
        FROM (
            SELECT
                checkin_session_id,
                CASE
                    WHEN BOOL_OR(escalation_type = 'EMERGENCY') THEN 'EMERGENCY'
                    WHEN BOOL_OR(escalation_type = 'SAME_DAY') THEN 'SAME_DAY'
                    ELSE 'ROUTINE'
                END AS escalation_type,
                MIN(checkin_escalation_id) AS retained_id
            FROM checkin_escalations
            GROUP BY checkin_session_id
        ) severity
        WHERE retained.checkin_escalation_id = severity.retained_id
        """
    )
    op.execute(
        """
        DELETE FROM checkin_escalations escalation
        USING (
            SELECT checkin_session_id, MIN(checkin_escalation_id) AS retained_id
            FROM checkin_escalations
            GROUP BY checkin_session_id
        ) canonical
        WHERE escalation.checkin_session_id = canonical.checkin_session_id
          AND escalation.checkin_escalation_id <> canonical.retained_id
        """
    )

    op.create_unique_constraint(
        "uq_checkin_escalations_session",
        "checkin_escalations",
        ["checkin_session_id"],
    )
    op.drop_index("ix_checkin_escalations_response", table_name="checkin_escalations")
    op.drop_constraint("fk_checkin_escalations_response", "checkin_escalations", type_="foreignkey")
    op.drop_column("checkin_escalations", "response_id")


def downgrade() -> None:
    op.add_column("checkin_escalations", sa.Column("response_id", sa.BigInteger(), nullable=True))
    op.execute(
        """
        UPDATE checkin_escalations escalation
        SET response_id = links.response_id
        FROM (
            SELECT checkin_escalation_id, MIN(response_id) AS response_id
            FROM checkin_escalation_responses
            GROUP BY checkin_escalation_id
        ) links
        WHERE escalation.checkin_escalation_id = links.checkin_escalation_id
        """
    )
    op.alter_column("checkin_escalations", "response_id", nullable=False)
    op.create_foreign_key(
        "fk_checkin_escalations_response",
        "checkin_escalations",
        "checkin_responses",
        ["response_id"],
        ["response_id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_checkin_escalations_response", "checkin_escalations", ["response_id"])
    op.drop_constraint("uq_checkin_escalations_session", "checkin_escalations", type_="unique")
    op.drop_table("checkin_escalation_responses")