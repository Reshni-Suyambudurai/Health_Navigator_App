"""Provision the City General Hospital clinical escalation queue.

Revision ID: c2d3e4f5a6b7
Revises: f1a2b3c4d5e6
Create Date: 2026-10-22 17:05:00
"""

from typing import Sequence, Union

from alembic import op


revision: str = "c2d3e4f5a6b7"
down_revision: Union[str, None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO care_team_queues (queue_id, organization_id, queue_name, queue_type, sla_minutes, status)
        SELECT 890002, o.organization_id, 'City General Clinical Review', 'CLINICAL', 120, 'ACTIVE'
        FROM organizations o
        WHERE o.organization_name = 'City General Hospital'
          AND NOT EXISTS (
              SELECT 1 FROM care_team_queues q
              WHERE q.organization_id = o.organization_id AND q.queue_type = 'CLINICAL' AND q.status = 'ACTIVE'
          );

                UPDATE users
                SET organization_id = (SELECT organization_id FROM organizations WHERE organization_name = 'City General Hospital')
                WHERE user_id = 3;

                DELETE FROM queue_memberships
                WHERE queue_id = 890002;

        INSERT INTO queue_memberships (queue_membership_id, queue_id, staff_id, role_in_queue, is_active)
                SELECT 890102, q.queue_id, sp.staff_id, 'PRIMARY', TRUE
        FROM care_team_queues q
        JOIN organizations o ON o.organization_id = q.organization_id
                JOIN staff_profiles sp ON sp.user_id = 3
        WHERE o.organization_name = 'City General Hospital'
          AND q.queue_type = 'CLINICAL'
          AND q.status = 'ACTIVE'
          AND NOT EXISTS (
              SELECT 1 FROM queue_memberships qm WHERE qm.queue_id = q.queue_id AND qm.staff_id = sp.staff_id
          );
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM queue_memberships WHERE queue_membership_id = 890102")
    op.execute("DELETE FROM care_team_queues WHERE queue_id = 890002")