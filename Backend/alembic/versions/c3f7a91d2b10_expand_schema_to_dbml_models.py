"""Expand schema to DBML-aligned models

Revision ID: c3f7a91d2b10
Revises: 880a89792d14
Create Date: 2026-10-17 17:20:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c3f7a91d2b10"
down_revision: Union[str, None] = "880a89792d14"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Existing table alignment
    op.execute("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS npi_number VARCHAR(20)")
    op.execute("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL")
    op.execute("CREATE INDEX IF NOT EXISTS ix_organizations_npi_number ON organizations (npi_number)")

    op.execute("ALTER TABLE patient_profiles ADD COLUMN IF NOT EXISTS external_fhir_patient_id VARCHAR(100)")
    op.execute("ALTER TABLE patient_profiles ADD COLUMN IF NOT EXISTS risk_tier VARCHAR(20) DEFAULT 'UNKNOWN' NOT NULL")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_patient_profiles_external_fhir_patient_id ON patient_profiles (external_fhir_patient_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_patient_profiles_risk_tier ON patient_profiles (risk_tier)")

    op.execute("ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS patient_id BIGINT")
    op.execute("ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS correlation_id VARCHAR(100)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_patient_id ON audit_logs (patient_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_correlation_id ON audit_logs (correlation_id)")
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'fk_audit_logs_patient_id'
            ) THEN
                ALTER TABLE audit_logs
                ADD CONSTRAINT fk_audit_logs_patient_id
                FOREIGN KEY (patient_id) REFERENCES patient_profiles(patient_id)
                ON DELETE SET NULL;
            END IF;
        END $$;
        """
    )

    # New tables
    op.create_table(
        "patient_consent_records",
        sa.Column("consent_id", sa.BigInteger(), nullable=False),
        sa.Column("patient_id", sa.BigInteger(), nullable=False),
        sa.Column("consent_type", sa.String(length=50), nullable=False),
        sa.Column("consent_status", sa.String(length=30), nullable=False),
        sa.Column("consent_text_version", sa.String(length=50), nullable=False),
        sa.Column("effective_at", sa.TIMESTAMP(), nullable=False),
        sa.Column("revoked_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("captured_channel", sa.String(length=30), nullable=False),
        sa.Column("captured_by_user_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["captured_by_user_id"], ["users.user_id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["patient_id"], ["patient_profiles.patient_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("consent_id"),
    )
    op.create_index("ix_patient_consent_records_patient_id", "patient_consent_records", ["patient_id"])
    op.create_index("ix_patient_consent_records_status", "patient_consent_records", ["consent_status"])

    op.create_table(
        "patient_enrollments",
        sa.Column("enrollment_id", sa.BigInteger(), nullable=False),
        sa.Column("patient_id", sa.BigInteger(), nullable=False),
        sa.Column("organization_id", sa.BigInteger(), nullable=False),
        sa.Column("enrollment_program", sa.String(length=50), nullable=False),
        sa.Column("enrollment_status", sa.String(length=30), nullable=False),
        sa.Column("enrollment_date", sa.TIMESTAMP(), nullable=False),
        sa.Column("close_date", sa.TIMESTAMP(), nullable=True),
        sa.Column("closed_reason", sa.String(length=255), nullable=True),
        sa.Column("created_by_user_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.user_id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.organization_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["patient_id"], ["patient_profiles.patient_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("enrollment_id"),
    )
    op.create_index("ix_patient_enrollments_patient_id", "patient_enrollments", ["patient_id"])
    op.create_index("ix_patient_enrollments_org_id", "patient_enrollments", ["organization_id"])
    op.create_index("ix_patient_enrollments_status", "patient_enrollments", ["enrollment_status"])

    op.create_table(
        "care_navigation_episodes",
        sa.Column("episode_id", sa.BigInteger(), nullable=False),
        sa.Column("patient_id", sa.BigInteger(), nullable=False),
        sa.Column("enrollment_id", sa.BigInteger(), nullable=False),
        sa.Column("episode_type", sa.String(length=80), nullable=False),
        sa.Column("trigger_type", sa.String(length=80), nullable=False),
        sa.Column("trigger_reference", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("opened_at", sa.TIMESTAMP(), nullable=False),
        sa.Column("closed_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("owner_staff_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["enrollment_id"], ["patient_enrollments.enrollment_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_staff_id"], ["staff_profiles.staff_id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["patient_id"], ["patient_profiles.patient_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("episode_id"),
    )
    op.create_index("ix_care_navigation_episodes_patient_id", "care_navigation_episodes", ["patient_id"])
    op.create_index("ix_care_navigation_episodes_status", "care_navigation_episodes", ["status"])

    op.create_table(
        "conversation_threads",
        sa.Column("thread_id", sa.BigInteger(), nullable=False),
        sa.Column("patient_id", sa.BigInteger(), nullable=False),
        sa.Column("episode_id", sa.BigInteger(), nullable=False),
        sa.Column("channel", sa.String(length=30), nullable=False),
        sa.Column("language", sa.String(length=15), nullable=False),
        sa.Column("started_at", sa.TIMESTAMP(), nullable=False),
        sa.Column("ended_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["episode_id"], ["care_navigation_episodes.episode_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["patient_id"], ["patient_profiles.patient_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("thread_id"),
    )
    op.create_index("ix_conversation_threads_patient_id", "conversation_threads", ["patient_id"])
    op.create_index("ix_conversation_threads_status", "conversation_threads", ["status"])

    op.create_table(
        "conversation_messages",
        sa.Column("message_id", sa.BigInteger(), nullable=False),
        sa.Column("thread_id", sa.BigInteger(), nullable=False),
        sa.Column("sender_type", sa.String(length=20), nullable=False),
        sa.Column("sender_user_id", sa.BigInteger(), nullable=True),
        sa.Column("ai_model_name", sa.String(length=80), nullable=True),
        sa.Column("ai_model_version", sa.String(length=40), nullable=True),
        sa.Column("message_text", sa.Text(), nullable=False),
        sa.Column("message_intent", sa.String(length=80), nullable=True),
        sa.Column("readability_grade", sa.Integer(), nullable=True),
        sa.Column("is_guardrail_override", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("message_metadata", sa.JSON(), nullable=True),
        sa.Column("sent_at", sa.TIMESTAMP(), nullable=False),
        sa.ForeignKeyConstraint(["sender_user_id"], ["users.user_id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["thread_id"], ["conversation_threads.thread_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("message_id"),
    )
    op.create_index("ix_conversation_messages_thread_id", "conversation_messages", ["thread_id"])
    op.create_index("ix_conversation_messages_sent_at", "conversation_messages", ["sent_at"])
    op.create_index("ix_conversation_messages_sender_type", "conversation_messages", ["sender_type"])

    op.create_table(
        "clinical_guardrail",
        sa.Column("guardrail_id", sa.BigInteger(), nullable=False),
        sa.Column("guardrail_name", sa.String(length=255), nullable=False),
        sa.Column("guardrail_markdown", sa.Text(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("guardrail_id"),
        sa.UniqueConstraint("guardrail_name"),
    )

    op.create_table(
        "clinical_guardrail_rules",
        sa.Column("rule_id", sa.BigInteger(), nullable=False),
        sa.Column("guardrail_id", sa.BigInteger(), nullable=False),
        sa.Column("rule_name", sa.String(length=255), nullable=False),
        sa.Column("rule_category", sa.String(length=50), nullable=False),
        sa.Column("urgency_level", sa.String(length=30), nullable=False),
        sa.Column("handler_role_id", sa.BigInteger(), nullable=True),
        sa.Column("action_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["guardrail_id"], ["clinical_guardrail.guardrail_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["handler_role_id"], ["roles.role_id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("rule_id"),
    )
    op.create_index("ix_clinical_guardrail_rules_guardrail_id", "clinical_guardrail_rules", ["guardrail_id"])
    op.create_index("ix_clinical_guardrail_rules_status", "clinical_guardrail_rules", ["status"])

    op.create_table(
        "conversation_guardrail_hits",
        sa.Column("guardrail_hit_id", sa.BigInteger(), nullable=False),
        sa.Column("thread_id", sa.BigInteger(), nullable=False),
        sa.Column("message_id", sa.BigInteger(), nullable=False),
        sa.Column("patient_id", sa.BigInteger(), nullable=False),
        sa.Column("rule_id", sa.BigInteger(), nullable=False),
        sa.Column("hit_urgency_level", sa.String(length=30), nullable=False),
        sa.Column("action_taken", sa.String(length=50), nullable=False),
        sa.Column("hit_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["message_id"], ["conversation_messages.message_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["patient_id"], ["patient_profiles.patient_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["rule_id"], ["clinical_guardrail_rules.rule_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["thread_id"], ["conversation_threads.thread_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("guardrail_hit_id"),
    )
    op.create_index("ix_conversation_guardrail_hits_thread_id", "conversation_guardrail_hits", ["thread_id"])
    op.create_index("ix_conversation_guardrail_hits_rule_id", "conversation_guardrail_hits", ["rule_id"])

    op.create_table(
        "emergency_events",
        sa.Column("emergency_event_id", sa.BigInteger(), nullable=False),
        sa.Column("patient_id", sa.BigInteger(), nullable=False),
        sa.Column("thread_id", sa.BigInteger(), nullable=False),
        sa.Column("guardrail_hit_id", sa.BigInteger(), nullable=False),
        sa.Column("emergency_type", sa.String(length=50), nullable=False),
        sa.Column("emergency_instruction_sent", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("notified_care_team", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("event_status", sa.String(length=30), nullable=False),
        sa.Column("detected_at", sa.TIMESTAMP(), nullable=False),
        sa.Column("resolved_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["guardrail_hit_id"], ["conversation_guardrail_hits.guardrail_hit_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["patient_id"], ["patient_profiles.patient_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["thread_id"], ["conversation_threads.thread_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("emergency_event_id"),
    )
    op.create_index("ix_emergency_events_patient_id", "emergency_events", ["patient_id"])
    op.create_index("ix_emergency_events_status", "emergency_events", ["event_status"])

    op.create_table(
        "care_team_queues",
        sa.Column("queue_id", sa.BigInteger(), nullable=False),
        sa.Column("organization_id", sa.BigInteger(), nullable=False),
        sa.Column("queue_name", sa.String(length=150), nullable=False),
        sa.Column("queue_type", sa.String(length=40), nullable=False),
        sa.Column("sla_minutes", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.organization_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("queue_id"),
    )
    op.create_index("ix_care_team_queues_org_id", "care_team_queues", ["organization_id"])

    op.create_table(
        "queue_memberships",
        sa.Column("queue_membership_id", sa.BigInteger(), nullable=False),
        sa.Column("queue_id", sa.BigInteger(), nullable=False),
        sa.Column("staff_id", sa.BigInteger(), nullable=False),
        sa.Column("role_in_queue", sa.String(length=30), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["queue_id"], ["care_team_queues.queue_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["staff_id"], ["staff_profiles.staff_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("queue_membership_id"),
        sa.UniqueConstraint("queue_id", "staff_id", name="uq_queue_memberships_queue_staff"),
    )

    op.create_table(
        "escalations",
        sa.Column("escalation_id", sa.BigInteger(), nullable=False),
        sa.Column("patient_id", sa.BigInteger(), nullable=False),
        sa.Column("episode_id", sa.BigInteger(), nullable=False),
        sa.Column("thread_id", sa.BigInteger(), nullable=False),
        sa.Column("guardrail_hit_id", sa.BigInteger(), nullable=True),
        sa.Column("queue_id", sa.BigInteger(), nullable=False),
        sa.Column("escalation_type", sa.String(length=40), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("patient_summary", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("resolved_at", sa.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(["episode_id"], ["care_navigation_episodes.episode_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["guardrail_hit_id"], ["conversation_guardrail_hits.guardrail_hit_id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["patient_id"], ["patient_profiles.patient_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["queue_id"], ["care_team_queues.queue_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["thread_id"], ["conversation_threads.thread_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("escalation_id"),
    )
    op.create_index("ix_escalations_queue_id", "escalations", ["queue_id"])
    op.create_index("ix_escalations_status", "escalations", ["status"])
    op.create_index("ix_escalations_priority", "escalations", ["priority"])

    op.create_table(
        "escalation_assignments",
        sa.Column("assignment_id", sa.BigInteger(), nullable=False),
        sa.Column("escalation_id", sa.BigInteger(), nullable=False),
        sa.Column("assigned_to_staff_id", sa.BigInteger(), nullable=True),
        sa.Column("assigned_by_user_id", sa.BigInteger(), nullable=True),
        sa.Column("assigned_at", sa.TIMESTAMP(), nullable=False),
        sa.Column("unassigned_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.ForeignKeyConstraint(["assigned_by_user_id"], ["users.user_id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assigned_to_staff_id"], ["staff_profiles.staff_id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["escalation_id"], ["escalations.escalation_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("assignment_id"),
    )
    op.create_index("ix_escalation_assignments_escalation_id", "escalation_assignments", ["escalation_id"])

    op.create_table(
        "escalation_actions",
        sa.Column("escalation_action_id", sa.BigInteger(), nullable=False),
        sa.Column("escalation_id", sa.BigInteger(), nullable=False),
        sa.Column("action_by_user_id", sa.BigInteger(), nullable=True),
        sa.Column("action_type", sa.String(length=40), nullable=False),
        sa.Column("action_notes", sa.Text(), nullable=True),
        sa.Column("action_at", sa.TIMESTAMP(), nullable=False),
        sa.ForeignKeyConstraint(["action_by_user_id"], ["users.user_id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["escalation_id"], ["escalations.escalation_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("escalation_action_id"),
    )
    op.create_index("ix_escalation_actions_escalation_id", "escalation_actions", ["escalation_id"])

    op.create_table(
        "outreach_campaigns",
        sa.Column("campaign_id", sa.BigInteger(), nullable=False),
        sa.Column("organization_id", sa.BigInteger(), nullable=False),
        sa.Column("campaign_name", sa.String(length=200), nullable=False),
        sa.Column("campaign_type", sa.String(length=50), nullable=False),
        sa.Column("target_cohort_definition", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_by_user_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.user_id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.organization_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("campaign_id"),
    )
    op.create_index("ix_outreach_campaigns_org_id", "outreach_campaigns", ["organization_id"])
    op.create_index("ix_outreach_campaigns_status", "outreach_campaigns", ["status"])

    op.create_table(
        "outreach_workflows",
        sa.Column("workflow_id", sa.BigInteger(), nullable=False),
        sa.Column("campaign_id", sa.BigInteger(), nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("step_name", sa.String(length=120), nullable=False),
        sa.Column("trigger_offset_hours", sa.Integer(), nullable=False),
        sa.Column("channel", sa.String(length=30), nullable=False),
        sa.Column("template_text", sa.Text(), nullable=False),
        sa.Column("escalation_on_no_response", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["outreach_campaigns.campaign_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("workflow_id"),
        sa.UniqueConstraint("campaign_id", "step_order", name="uq_outreach_workflows_campaign_step"),
    )

    op.create_table(
        "outreach_events",
        sa.Column("outreach_event_id", sa.BigInteger(), nullable=False),
        sa.Column("patient_id", sa.BigInteger(), nullable=False),
        sa.Column("episode_id", sa.BigInteger(), nullable=False),
        sa.Column("campaign_id", sa.BigInteger(), nullable=False),
        sa.Column("workflow_id", sa.BigInteger(), nullable=False),
        sa.Column("channel", sa.String(length=30), nullable=False),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("delivery_status", sa.String(length=20), nullable=False),
        sa.Column("scheduled_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("sent_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("responded_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["outreach_campaigns.campaign_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["episode_id"], ["care_navigation_episodes.episode_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["patient_id"], ["patient_profiles.patient_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workflow_id"], ["outreach_workflows.workflow_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("outreach_event_id"),
    )
    op.create_index("ix_outreach_events_patient_id", "outreach_events", ["patient_id"])
    op.create_index("ix_outreach_events_status", "outreach_events", ["delivery_status"])


def downgrade() -> None:
    op.drop_index("ix_outreach_events_status", table_name="outreach_events")
    op.drop_index("ix_outreach_events_patient_id", table_name="outreach_events")
    op.drop_table("outreach_events")
    op.drop_table("outreach_workflows")
    op.drop_index("ix_outreach_campaigns_status", table_name="outreach_campaigns")
    op.drop_index("ix_outreach_campaigns_org_id", table_name="outreach_campaigns")
    op.drop_table("outreach_campaigns")
    op.drop_index("ix_escalation_actions_escalation_id", table_name="escalation_actions")
    op.drop_table("escalation_actions")
    op.drop_index("ix_escalation_assignments_escalation_id", table_name="escalation_assignments")
    op.drop_table("escalation_assignments")
    op.drop_index("ix_escalations_priority", table_name="escalations")
    op.drop_index("ix_escalations_status", table_name="escalations")
    op.drop_index("ix_escalations_queue_id", table_name="escalations")
    op.drop_table("escalations")
    op.drop_table("queue_memberships")
    op.drop_index("ix_care_team_queues_org_id", table_name="care_team_queues")
    op.drop_table("care_team_queues")
    op.drop_index("ix_emergency_events_status", table_name="emergency_events")
    op.drop_index("ix_emergency_events_patient_id", table_name="emergency_events")
    op.drop_table("emergency_events")
    op.drop_index("ix_conversation_guardrail_hits_rule_id", table_name="conversation_guardrail_hits")
    op.drop_index("ix_conversation_guardrail_hits_thread_id", table_name="conversation_guardrail_hits")
    op.drop_table("conversation_guardrail_hits")
    op.drop_index("ix_clinical_guardrail_rules_status", table_name="clinical_guardrail_rules")
    op.drop_index("ix_clinical_guardrail_rules_guardrail_id", table_name="clinical_guardrail_rules")
    op.drop_table("clinical_guardrail_rules")
    op.drop_table("clinical_guardrail")
    op.drop_index("ix_conversation_messages_sender_type", table_name="conversation_messages")
    op.drop_index("ix_conversation_messages_sent_at", table_name="conversation_messages")
    op.drop_index("ix_conversation_messages_thread_id", table_name="conversation_messages")
    op.drop_table("conversation_messages")
    op.drop_index("ix_conversation_threads_status", table_name="conversation_threads")
    op.drop_index("ix_conversation_threads_patient_id", table_name="conversation_threads")
    op.drop_table("conversation_threads")
    op.drop_index("ix_care_navigation_episodes_status", table_name="care_navigation_episodes")
    op.drop_index("ix_care_navigation_episodes_patient_id", table_name="care_navigation_episodes")
    op.drop_table("care_navigation_episodes")
    op.drop_index("ix_patient_enrollments_status", table_name="patient_enrollments")
    op.drop_index("ix_patient_enrollments_org_id", table_name="patient_enrollments")
    op.drop_index("ix_patient_enrollments_patient_id", table_name="patient_enrollments")
    op.drop_table("patient_enrollments")
    op.drop_index("ix_patient_consent_records_status", table_name="patient_consent_records")
    op.drop_index("ix_patient_consent_records_patient_id", table_name="patient_consent_records")
    op.drop_table("patient_consent_records")
