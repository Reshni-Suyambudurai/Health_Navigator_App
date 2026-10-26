"""Add deterministic database-backed patient chat guardrails.

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-10-22 18:30:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d3e4f5a6b7c8"
down_revision: Union[str, None] = "c2d3e4f5a6b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("clinical_guardrail_rules", sa.Column("patient_response_template", sa.Text(), nullable=True))
    op.add_column("clinical_guardrail_rules", sa.Column("target_queue_type", sa.String(length=50), nullable=True))
    op.add_column("clinical_guardrail_rules", sa.Column("escalation_type", sa.String(length=50), nullable=True))
    op.add_column("clinical_guardrail_rules", sa.Column("escalation_priority", sa.String(length=30), nullable=True))

    op.create_table(
        "clinical_guardrail_matchers",
        sa.Column("matcher_id", sa.BigInteger(), nullable=False),
        sa.Column("rule_id", sa.BigInteger(), nullable=False),
        sa.Column("pattern", sa.String(length=500), nullable=False),
        sa.Column("match_type", sa.String(length=30), nullable=False),
        sa.Column("priority", sa.Integer(), server_default="100", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["rule_id"], ["clinical_guardrail_rules.rule_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("matcher_id"),
        sa.UniqueConstraint("rule_id", "pattern", name="uq_clinical_guardrail_matcher_rule_pattern"),
    )
    op.create_index("ix_clinical_guardrail_matchers_rule_id", "clinical_guardrail_matchers", ["rule_id"])
    op.create_index("ix_clinical_guardrail_matchers_is_active", "clinical_guardrail_matchers", ["is_active"])

    op.execute(
        """
        INSERT INTO clinical_guardrail (guardrail_id, guardrail_name, guardrail_markdown)
        SELECT 860002, 'BRD Core Patient Safety Guardrails',
               'Deterministic patient-chat safety policies. Matched messages bypass the language model and create an auditable care-team escalation.'
        WHERE NOT EXISTS (SELECT 1 FROM clinical_guardrail WHERE guardrail_id = 860002);

        INSERT INTO clinical_guardrail_rules (
            rule_id, guardrail_id, rule_name, rule_category, urgency_level, handler_role_id,
            action_type, status, patient_response_template, target_queue_type, escalation_type, escalation_priority
        )
        SELECT 870101, 860002, 'Emergency medical symptoms', 'EMERGENCY', 'EMERGENCY', r.role_id,
               'EMERGENCY_PROTOCOL', 'ACTIVE',
               'This could be an emergency. Call 911 now. Do not wait for a reply here or drive yourself. If you can, ask someone nearby to stay with you.',
               'EMERGENCY', 'EMERGENCY', 'CRITICAL'
        FROM roles r
        WHERE r.role_name = 'TRANSITIONAL_CARE_NURSE'
          AND NOT EXISTS (SELECT 1 FROM clinical_guardrail_rules WHERE rule_id = 870101);

        INSERT INTO clinical_guardrail_rules (
            rule_id, guardrail_id, rule_name, rule_category, urgency_level, handler_role_id,
            action_type, status, patient_response_template, target_queue_type, escalation_type, escalation_priority
        )
        SELECT 870102, 860002, 'Self-harm or suicide risk', 'EMERGENCY', 'EMERGENCY', r.role_id,
               'EMERGENCY_PROTOCOL', 'ACTIVE',
               'Your safety matters. Call or text 988 now for the Suicide and Crisis Lifeline, or call 911 if you may act on these thoughts or are in immediate danger. Please do not stay alone.',
               'EMERGENCY', 'EMERGENCY', 'CRITICAL'
        FROM roles r
        WHERE r.role_name = 'TRANSITIONAL_CARE_NURSE'
          AND NOT EXISTS (SELECT 1 FROM clinical_guardrail_rules WHERE rule_id = 870102);

        INSERT INTO clinical_guardrail_rules (
            rule_id, guardrail_id, rule_name, rule_category, urgency_level, handler_role_id,
            action_type, status, patient_response_template, target_queue_type, escalation_type, escalation_priority
        )
        SELECT 870201, 860002, 'Medication dose or schedule change', 'MEDICATION', 'SAME_DAY', r.role_id,
               'ESCALATE', 'ACTIVE',
               'I cannot tell you to start, stop, skip, or change a medicine. Please do not change it until you speak with your care team. I have sent this for same-day review.',
               'MEDICATION', 'MEDICATION', 'HIGH'
        FROM roles r
        WHERE r.role_name = 'TRANSITIONAL_CARE_NURSE'
          AND NOT EXISTS (SELECT 1 FROM clinical_guardrail_rules WHERE rule_id = 870201);

        INSERT INTO clinical_guardrail_rules (
            rule_id, guardrail_id, rule_name, rule_category, urgency_level, handler_role_id,
            action_type, status, patient_response_template, target_queue_type, escalation_type, escalation_priority
        )
        SELECT 870202, 860002, 'Medication safety concern', 'MEDICATION', 'SAME_DAY', r.role_id,
               'ESCALATE', 'ACTIVE',
               'A care-team member should review this medication concern today. Do not make a medication change based on this chat. I have sent your message for review.',
               'MEDICATION', 'MEDICATION', 'HIGH'
        FROM roles r
        WHERE r.role_name = 'TRANSITIONAL_CARE_NURSE'
          AND NOT EXISTS (SELECT 1 FROM clinical_guardrail_rules WHERE rule_id = 870202);

        INSERT INTO clinical_guardrail_rules (
            rule_id, guardrail_id, rule_name, rule_category, urgency_level, handler_role_id,
            action_type, status, patient_response_template, target_queue_type, escalation_type, escalation_priority
        )
        SELECT 870301, 860002, 'Urgent post-discharge symptom', 'SYMPTOM', 'SAME_DAY', r.role_id,
               'ESCALATE', 'ACTIVE',
               'Your care team should review these symptoms today. I have sent a same-day request to the transitional-care nurse. Call 911 now if symptoms become severe or you have chest pain, trouble breathing, or stroke signs.',
               'CLINICAL', 'CLINICAL_REVIEW', 'HIGH'
        FROM roles r
        WHERE r.role_name = 'TRANSITIONAL_CARE_NURSE'
          AND NOT EXISTS (SELECT 1 FROM clinical_guardrail_rules WHERE rule_id = 870301);

        INSERT INTO clinical_guardrail_rules (
            rule_id, guardrail_id, rule_name, rule_category, urgency_level, handler_role_id,
            action_type, status, patient_response_template, target_queue_type, escalation_type, escalation_priority
        )
        SELECT 870401, 860002, 'Clinical diagnosis or result interpretation', 'CLINICAL_SCOPE', 'ROUTINE', r.role_id,
               'ESCALATE', 'ACTIVE',
               'I cannot diagnose a condition or interpret a test result. I have sent your question to the care team for follow-up.',
               'CLINICAL', 'CLINICAL_REVIEW', 'MEDIUM'
        FROM roles r
        WHERE r.role_name = 'TRANSITIONAL_CARE_NURSE'
          AND NOT EXISTS (SELECT 1 FROM clinical_guardrail_rules WHERE rule_id = 870401);
        """
    )

    matchers = (
        (871001, 870101, "chest pain"), (871002, 870101, "chest pressure"),
        (871003, 870101, "trouble breathing"), (871004, 870101, "cannot breathe"),
        (871005, 870101, "can't breathe"), (871006, 870101, "shortness of breath"),
        (871007, 870101, "face droop"), (871008, 870101, "slurred speech"),
        (871009, 870101, "one-sided weakness"), (871010, 870101, "unconscious"),
        (871011, 870101, "severe bleeding"), (871012, 870101, "overdose"),
        (871013, 870101, "poisoning"), (871014, 870101, "tongue swelling"),
        (871015, 870101, "swelling of my throat"),
        (871101, 870102, "kill myself"), (871102, 870102, "want to die"),
        (871103, 870102, "suicidal"), (871104, 870102, "hurt myself"),
        (871105, 870102, "self harm"),
        (871201, 870201, "stop taking"), (871202, 870201, "start taking"),
        (871203, 870201, "increase dose"), (871204, 870201, "decrease dose"),
        (871205, 870201, "reduce dose"), (871206, 870201, "change dose"),
        (871207, 870201, "skip dose"), (871208, 870201, "double dose"),
        (871209, 870201, "missed dose"), (871210, 870201, "wrong dose"),
        (871301, 870202, "side effect"), (871302, 870202, "medication interaction"),
        (871303, 870202, "medicine interaction"), (871304, 870202, "reaction to my medication"),
        (871401, 870301, "severe dizziness"), (871402, 870301, "repeated falls"),
        (871403, 870301, "rapid weight gain"), (871404, 870301, "cannot keep fluids down"),
        (871405, 870301, "worsening pain"), (871406, 870301, "confusion"),
        (871501, 870401, "diagnose me"), (871502, 870401, "do i have cancer"),
        (871503, 870401, "what do my labs mean"), (871504, 870401, "interpret my lab"),
        (871505, 870401, "what does my scan mean"), (871506, 870401, "interpret my scan"),
    )
    bind = op.get_bind()
    for matcher_id, rule_id, pattern in matchers:
        bind.execute(
            sa.text(
                """
                INSERT INTO clinical_guardrail_matchers (matcher_id, rule_id, pattern, match_type, priority, is_active)
                SELECT :matcher_id, :rule_id, :pattern, 'PHRASE', 100, TRUE
                WHERE EXISTS (SELECT 1 FROM clinical_guardrail_rules WHERE rule_id = :rule_id)
                  AND NOT EXISTS (SELECT 1 FROM clinical_guardrail_matchers WHERE matcher_id = :matcher_id)
                """
            ),
            {"matcher_id": matcher_id, "rule_id": rule_id, "pattern": pattern},
        )


def downgrade() -> None:
    op.drop_index("ix_clinical_guardrail_matchers_is_active", table_name="clinical_guardrail_matchers")
    op.drop_index("ix_clinical_guardrail_matchers_rule_id", table_name="clinical_guardrail_matchers")
    op.drop_table("clinical_guardrail_matchers")
    op.drop_column("clinical_guardrail_rules", "escalation_priority")
    op.drop_column("clinical_guardrail_rules", "escalation_type")
    op.drop_column("clinical_guardrail_rules", "target_queue_type")
    op.drop_column("clinical_guardrail_rules", "patient_response_template")