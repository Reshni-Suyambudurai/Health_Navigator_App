"""Merge the runtime and check-in schema migration branches.

Revision ID: merge_checkin_20261028
Revises: e1f2a3b4c5d6, fd4e5f6a7b8c
"""

from typing import Sequence, Union


revision: str = "merge_checkin_20261028"
down_revision: Union[str, tuple[str, str], None] = ("e1f2a3b4c5d6", "fd4e5f6a7b8c")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
