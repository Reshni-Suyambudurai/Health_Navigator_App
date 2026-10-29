"""Reset documented demo user passwords.

Revision ID: f2a3b4c5d6e7
Revises: e8a6c1f4b2d3
Create Date: 2026-10-21 11:15:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f2a3b4c5d6e7"
down_revision: Union[str, None] = "e8a6c1f4b2d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


DEMO_EMAILS = (
    "john.doe@example.com",
    "sarah.johnson@cityhospital.com",
    "michael.chen@communityclinic.com",
    "emma.williams@midwesthealthcare.com",
    "demo.admin@patientai.local",
    "care.manager@patientai.local",
    "aguns790.2310@patientai.local",
    "bettyann83.3942@patientai.local",
    "carl856.5991@patientai.local",
)

DEMO_PASSWORD_HASH = "$2b$12$lf3AMdaBvULOm4l3Wo//7.Y6hUiWZcRwVLjWqsVWG5ef0Zb6F5sim"


def upgrade() -> None:
    op.get_bind().execute(
        sa.text(
            """
            UPDATE users
            SET password_hash = :password_hash,
                updated_at = CURRENT_TIMESTAMP
            WHERE email IN :emails
            """
        ).bindparams(sa.bindparam("emails", expanding=True)),
        {"password_hash": DEMO_PASSWORD_HASH, "emails": DEMO_EMAILS},
    )


def downgrade() -> None:
    pass