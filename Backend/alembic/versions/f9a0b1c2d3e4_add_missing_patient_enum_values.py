"""Add enum values used by the patient profile model.

Revision ID: f9a0b1c2d3e4
Revises: f8a9b0c1d2e3
"""

from typing import Sequence, Union

from alembic import op


revision: str = "f9a0b1c2d3e4"
down_revision: Union[str, None] = "f8a9b0c1d2e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE gender ADD VALUE IF NOT EXISTS 'UNKNOWN'")
    op.execute("ALTER TYPE gender ADD VALUE IF NOT EXISTS 'NOT_DISCLOSED'")
    op.execute("ALTER TYPE contact_method ADD VALUE IF NOT EXISTS 'EMAIL'")
    op.execute("ALTER TYPE contact_method ADD VALUE IF NOT EXISTS 'PHONE'")
    op.execute(
        "UPDATE patient_profiles SET preferred_contact_method = 'PORTAL' "
        "WHERE preferred_contact_method = 'WEB'"
    )
    op.execute(
        "UPDATE patient_profiles SET preferred_contact_method = 'PHONE' "
        "WHERE preferred_contact_method = 'VOICE'"
    )


def downgrade() -> None:
    # PostgreSQL does not support removing enum values safely in-place.
    pass