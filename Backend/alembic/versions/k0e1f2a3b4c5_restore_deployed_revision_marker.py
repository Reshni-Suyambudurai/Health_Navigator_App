"""Restore the deployed revision marker missing from source history.

Revision ID: k0e1f2a3b4c5
Revises: j9e0f1a2b3c4
"""

from typing import Sequence, Union


revision: str = "k0e1f2a3b4c5"
down_revision: Union[str, None] = "j9e0f1a2b3c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass