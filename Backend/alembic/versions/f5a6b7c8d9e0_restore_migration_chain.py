"""Restore the migration chain after removed outreach audit persistence.

Revision ID: f5a6b7c8d9e0
Revises: a7c8d9e0f1b2

The database was stamped with this revision before outreach audit persistence
was removed. Its schema changes are intentionally not replayed; retaining this
no-op revision lets existing databases continue to later migrations safely.
"""

from typing import Union


revision: str = "f5a6b7c8d9e0"
down_revision: Union[str, None] = "a7c8d9e0f1b2"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass