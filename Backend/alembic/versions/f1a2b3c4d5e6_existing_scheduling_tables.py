"""Compatibility marker for scheduling tables created outside this repository.

Revision ID: f1a2b3c4d5e6
Revises: e8a6c1f4b2d3

This revision records the schema state found in an existing database. The
following revision owns the reproducible table creation for fresh databases.
"""
from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, None] = "e8a6c1f4b2d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
