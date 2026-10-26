"""Add the emergency-paused patient conversation state.

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-10-23 12:00:00
"""

from typing import Sequence, Union

from alembic import op


revision: str = "f5a6b7c8d9e0"
down_revision: Union[str, None] = "e4f5a6b7c8d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # conversation_threads.status is VARCHAR(30) in the existing schema.
    # The new application-level status needs no physical schema change.
    pass


def downgrade() -> None:
    pass