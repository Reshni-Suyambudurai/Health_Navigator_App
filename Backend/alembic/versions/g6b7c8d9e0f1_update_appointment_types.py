"""Replace legacy appointment types with routine and check-in types."""

from typing import Sequence, Union

from alembic import op


revision: str = "g6b7c8d9e0f1"
down_revision: Union[str, None] = "merge_checkin_20261028"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE appointment_type RENAME TO appointment_type_legacy")
    op.execute("CREATE TYPE appointment_type AS ENUM ('ROUTINE', 'CHECK-IN')")
    op.execute(
        """
        ALTER TABLE appointments
        ALTER COLUMN appointment_type TYPE appointment_type
        USING 'ROUTINE'::appointment_type
        """
    )
    op.execute("DROP TYPE appointment_type_legacy")


def downgrade() -> None:
    op.execute("ALTER TYPE appointment_type RENAME TO appointment_type_new")
    op.execute(
        """
        CREATE TYPE appointment_type AS ENUM (
            'POST_DISCHARGE',
            'NURSE_FOLLOWUP',
            'CARE_MANAGER_CALL'
        )
        """
    )
    op.execute(
        """
        ALTER TABLE appointments
        ALTER COLUMN appointment_type TYPE appointment_type
        USING 'POST_DISCHARGE'::appointment_type
        """
    )
    op.execute("DROP TYPE appointment_type_new")
