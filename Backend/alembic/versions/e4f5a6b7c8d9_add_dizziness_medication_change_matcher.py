"""Add a symptom and medication-change guardrail matcher.

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
Create Date: 2026-10-23 11:20:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e4f5a6b7c8d9"
down_revision: Union[str, None] = "d3e4f5a6b7c8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.get_bind().execute(
        sa.text(
            """
            INSERT INTO clinical_guardrail_matchers (
                matcher_id, rule_id, pattern, match_type, priority, is_active
            )
            SELECT 871211, 870201, 'dizz|stop my', 'ALL_TERMS', 10, TRUE
            WHERE EXISTS (SELECT 1 FROM clinical_guardrail_rules WHERE rule_id = 870201)
              AND NOT EXISTS (
                  SELECT 1
                  FROM clinical_guardrail_matchers
                  WHERE rule_id = 870201 AND pattern = 'dizz|stop my'
              )
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            DELETE FROM clinical_guardrail_matchers
            WHERE rule_id = 870201 AND pattern = 'dizz|stop my'
            """
        )
    )