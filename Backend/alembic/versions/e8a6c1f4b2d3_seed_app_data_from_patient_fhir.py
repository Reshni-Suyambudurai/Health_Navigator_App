"""Seed app data from patientFHIR for local setup

Revision ID: e8a6c1f4b2d3
Revises: c3f7a91d2b10
Create Date: 2026-10-17 19:10:00

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "e8a6c1f4b2d3"
down_revision: Union[str, None] = "c3f7a91d2b10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ensure one organization and baseline roles exist for local login/testing.
    op.execute(
        """
        INSERT INTO organizations (organization_name, organization_type, address, phone, status)
        VALUES ('Patient AI Demo Org', 'HOSPITAL', '100 Demo Street, Boston, MA', '555-0101', 'ACTIVE')
        ON CONFLICT (organization_name) DO NOTHING;
        """
    )

    op.execute(
        """
        INSERT INTO roles (role_name, description)
        VALUES ('SYSTEM_ADMIN', 'Dummy system admin role for local seeded login')
        ON CONFLICT (role_name) DO NOTHING;
        """
    )

    op.execute(
        """
        INSERT INTO roles (role_name, description)
        VALUES ('CARE_MANAGER', 'Dummy care manager role for seeded workflow data')
        ON CONFLICT (role_name) DO NOTHING;
        """
    )

    # Seed one login-ready admin user.
    op.execute(
        """
        INSERT INTO users (
            organization_id, role_id, first_name, last_name, email, password_hash, phone, status, is_verified
        )
        SELECT
            o.organization_id,
            r.role_id,
            'Demo',
            'Admin',
            'demo.admin@patientai.local',
            '$2b$12$V12E2/Wv1pmO2pQo/dUW/uR/3QpaluMOXPREt3TyJEcwEly/8jNcS',
            '555-1100',
            'ACTIVE',
            TRUE
        FROM organizations o
        JOIN roles r ON r.role_name = 'SYSTEM_ADMIN'
        WHERE o.organization_name = 'Patient AI Demo Org'
          AND NOT EXISTS (
              SELECT 1 FROM users u WHERE u.email = 'demo.admin@patientai.local'
          );
        """
    )

    # Seed one care manager user + staff profile to support queue membership and assignments.
    op.execute(
        """
        INSERT INTO users (
            user_id, organization_id, role_id, first_name, last_name, email, password_hash, phone, status, is_verified
        )
        SELECT
            990001,
            o.organization_id,
            r.role_id,
            'Care',
            'Manager',
            'care.manager@patientai.local',
            '$2b$12$V12E2/Wv1pmO2pQo/dUW/uR/3QpaluMOXPREt3TyJEcwEly/8jNcS',
            '555-1200',
            'ACTIVE',
            TRUE
        FROM organizations o
        JOIN roles r ON r.role_name = 'CARE_MANAGER'
        WHERE o.organization_name = 'Patient AI Demo Org'
          AND NOT EXISTS (
              SELECT 1 FROM users u WHERE u.user_id = 990001 OR u.email = 'care.manager@patientai.local'
          );
        """
    )

    op.execute(
        """
        INSERT INTO staff_profiles (
            staff_id, user_id, employee_id, license_number, license_type, department, specialization
        )
        SELECT
            880001,
            990001,
            'CM-0001',
            'RN-0001',
            'Registered Nurse',
            'Care Navigation',
            'Transitional Care'
        WHERE NOT EXISTS (
            SELECT 1 FROM staff_profiles sp WHERE sp.staff_id = 880001 OR sp.user_id = 990001
        );
        """
    )

    # Insert patientFHIR sample patients into app tables: users + patient_profiles.
    op.execute(
        """
        INSERT INTO users (
            user_id, organization_id, role_id, first_name, last_name, email, password_hash, phone, status, is_verified
        )
        SELECT 910001, o.organization_id, r.role_id, 'Agnus790', 'Brown30', 'aguns790.2310@patientai.local',
             '$2b$12$V12E2/Wv1pmO2pQo/dUW/uR/3QpaluMOXPREt3TyJEcwEly/8jNcS', '555-886-8907', 'ACTIVE', TRUE
        FROM organizations o
        JOIN roles r ON r.role_name = 'PATIENT'
        WHERE o.organization_name = 'Patient AI Demo Org'
          AND NOT EXISTS (SELECT 1 FROM users WHERE user_id = 910001 OR email = 'aguns790.2310@patientai.local');

        INSERT INTO users (
            user_id, organization_id, role_id, first_name, last_name, email, password_hash, phone, status, is_verified
        )
        SELECT 910002, o.organization_id, r.role_id, 'Bettyann83', 'Christiansen251', 'bettyann83.3942@patientai.local',
             '$2b$12$V12E2/Wv1pmO2pQo/dUW/uR/3QpaluMOXPREt3TyJEcwEly/8jNcS', '555-691-5306', 'ACTIVE', TRUE
        FROM organizations o
        JOIN roles r ON r.role_name = 'PATIENT'
        WHERE o.organization_name = 'Patient AI Demo Org'
          AND NOT EXISTS (SELECT 1 FROM users WHERE user_id = 910002 OR email = 'bettyann83.3942@patientai.local');

        INSERT INTO users (
            user_id, organization_id, role_id, first_name, last_name, email, password_hash, phone, status, is_verified
        )
        SELECT 910003, o.organization_id, r.role_id, 'Carl856', 'Fadel536', 'carl856.5991@patientai.local',
             '$2b$12$V12E2/Wv1pmO2pQo/dUW/uR/3QpaluMOXPREt3TyJEcwEly/8jNcS', '555-977-5003', 'ACTIVE', TRUE
        FROM organizations o
        JOIN roles r ON r.role_name = 'PATIENT'
        WHERE o.organization_name = 'Patient AI Demo Org'
          AND NOT EXISTS (SELECT 1 FROM users WHERE user_id = 910003 OR email = 'carl856.5991@patientai.local');
        """
    )

    op.execute(
        """
        INSERT INTO patient_profiles (
            patient_id, user_id, external_fhir_patient_id, date_of_birth, gender,
            preferred_language, preferred_contact_method, emergency_contact_name,
            emergency_contact_phone, risk_tier
        )
        VALUES (
            810001, 910001, '2310', '1990-11-15', 'FEMALE',
            'en-US', 'SMS', 'Ona426 Brown30', '555-886-8907', 'MEDIUM'
        )
        ON CONFLICT (external_fhir_patient_id) DO NOTHING;

        INSERT INTO patient_profiles (
            patient_id, user_id, external_fhir_patient_id, date_of_birth, gender,
            preferred_language, preferred_contact_method, emergency_contact_name,
            emergency_contact_phone, risk_tier
        )
        VALUES (
            810002, 910002, '3942', '1962-02-22', 'FEMALE',
            'en-US', 'SMS', 'Raye931 Christiansen251', '555-691-5306', 'HIGH'
        )
        ON CONFLICT (external_fhir_patient_id) DO NOTHING;

        INSERT INTO patient_profiles (
            patient_id, user_id, external_fhir_patient_id, date_of_birth, gender,
            preferred_language, preferred_contact_method, emergency_contact_name,
            emergency_contact_phone, risk_tier
        )
        VALUES (
            810003, 910003, '5991', '1959-08-08', 'FEMALE',
            'en-US', 'SMS', 'Kyung736 Fadel536', '555-977-5003', 'HIGH'
        )
        ON CONFLICT (external_fhir_patient_id) DO NOTHING;
        """
    )

    # Patient program/enrollment-related seed data.
    op.execute(
        """
        INSERT INTO patient_enrollments (
            enrollment_id, patient_id, organization_id, enrollment_program, enrollment_status,
            enrollment_date, created_by_user_id
        )
        SELECT 820001, 810001, o.organization_id, 'CARE_NAVIGATION', 'ACTIVE', CURRENT_TIMESTAMP, 990001
        FROM organizations o
        WHERE o.organization_name = 'Patient AI Demo Org'
          AND NOT EXISTS (SELECT 1 FROM patient_enrollments pe WHERE pe.enrollment_id = 820001);

        INSERT INTO care_navigation_episodes (
            episode_id, patient_id, enrollment_id, episode_type, trigger_type, trigger_reference,
            status, opened_at, owner_staff_id
        )
        VALUES (830001, 810001, 820001, 'POST_DISCHARGE', 'FHIR_ENCOUNTER', 'Encounter/2311', 'OPEN', CURRENT_TIMESTAMP, 880001)
        ON CONFLICT (episode_id) DO NOTHING;

        INSERT INTO conversation_threads (
            thread_id, patient_id, episode_id, channel, language, started_at, status
        )
        VALUES (840001, 810001, 830001, 'SMS', 'en-US', CURRENT_TIMESTAMP, 'ACTIVE')
        ON CONFLICT (thread_id) DO NOTHING;

        INSERT INTO conversation_messages (
            message_id, thread_id, sender_type, sender_user_id, ai_model_name, ai_model_version,
            message_text, message_intent, readability_grade, is_guardrail_override, sent_at
        )
        VALUES (
            850001,
            840001,
            'PATIENT',
            910001,
            'gpt-4.1',
            'seed',
            'I am feeling dizzy after my visit and need help.',
            'symptom_followup',
            7,
            FALSE,
            CURRENT_TIMESTAMP
        )
        ON CONFLICT (message_id) DO NOTHING;
        """
    )

    # Clinical guardrail + rule seed data.
    op.execute(
        """
        INSERT INTO clinical_guardrail (guardrail_id, guardrail_name, guardrail_markdown)
        VALUES (
            860001,
            'Emergency Symptoms Escalation Guardrail',
            'If patient reports chest pain, breathing difficulty, or severe dizziness, escalate immediately to care team.'
        )
        ON CONFLICT (guardrail_name) DO NOTHING;

        INSERT INTO clinical_guardrail_rules (
            rule_id, guardrail_id, rule_name, rule_category, urgency_level, handler_role_id, action_type, status
        )
        SELECT
            870001,
            860001,
            'Severe dizziness requires urgent triage',
            'SYMPTOM_SAFETY',
            'HIGH',
            r.role_id,
            'CREATE_ESCALATION',
            'ACTIVE'
        FROM roles r
        WHERE r.role_name = 'CARE_MANAGER'
          AND NOT EXISTS (
              SELECT 1 FROM clinical_guardrail_rules gr WHERE gr.rule_id = 870001
          );

        INSERT INTO conversation_guardrail_hits (
            guardrail_hit_id, thread_id, message_id, patient_id, rule_id, hit_urgency_level, action_taken, hit_reason
        )
        VALUES (
            880101,
            840001,
            850001,
            810001,
            870001,
            'HIGH',
            'ESCALATED',
            'Seeded guardrail hit for symptom safety workflow testing'
        )
        ON CONFLICT (guardrail_hit_id) DO NOTHING;
        """
    )

    # Care team queue + membership + outreach campaign/workflow seed data.
    op.execute(
        """
        INSERT INTO care_team_queues (
            queue_id, organization_id, queue_name, queue_type, sla_minutes, status
        )
        SELECT 890001, o.organization_id, 'Urgent Symptom Queue', 'CLINICAL', 30, 'ACTIVE'
        FROM organizations o
        WHERE o.organization_name = 'Patient AI Demo Org'
          AND NOT EXISTS (SELECT 1 FROM care_team_queues q WHERE q.queue_id = 890001);

        INSERT INTO queue_memberships (
            queue_membership_id, queue_id, staff_id, role_in_queue, is_active
        )
        VALUES (890101, 890001, 880001, 'PRIMARY', TRUE)
        ON CONFLICT (queue_id, staff_id) DO NOTHING;

        INSERT INTO escalations (
            escalation_id, patient_id, episode_id, thread_id, guardrail_hit_id, queue_id,
            escalation_type, priority, reason, patient_summary, status
        )
        VALUES (
            895001,
            810001,
            830001,
            840001,
            880101,
            890001,
            'CLINICAL_REVIEW',
            'HIGH',
            'Seeded escalation from guardrail hit',
            'Patient reported dizziness post encounter.',
            'OPEN'
        )
        ON CONFLICT (escalation_id) DO NOTHING;

        INSERT INTO escalation_assignments (
            assignment_id, escalation_id, assigned_to_staff_id, assigned_by_user_id, assigned_at, is_active
        )
        VALUES (896001, 895001, 880001, 990001, CURRENT_TIMESTAMP, TRUE)
        ON CONFLICT (assignment_id) DO NOTHING;

        INSERT INTO escalation_actions (
            escalation_action_id, escalation_id, action_by_user_id, action_type, action_notes, action_at
        )
        VALUES (
            897001,
            895001,
            990001,
            'TRIAGE_STARTED',
            'Initial triage initiated by seeded care manager.',
            CURRENT_TIMESTAMP
        )
        ON CONFLICT (escalation_action_id) DO NOTHING;

        INSERT INTO outreach_campaigns (
            campaign_id, organization_id, campaign_name, campaign_type, target_cohort_definition,
            status, created_by_user_id
        )
        SELECT
            898001,
            o.organization_id,
            'Post-Discharge Follow-up Campaign',
            'FOLLOW_UP',
            '{"cohort":"post_discharge_high_risk"}'::json,
            'ACTIVE',
            990001
        FROM organizations o
        WHERE o.organization_name = 'Patient AI Demo Org'
          AND NOT EXISTS (SELECT 1 FROM outreach_campaigns oc WHERE oc.campaign_id = 898001);

        INSERT INTO outreach_workflows (
            workflow_id, campaign_id, step_order, step_name, trigger_offset_hours, channel,
            template_text, escalation_on_no_response
        )
        VALUES (
            899001,
            898001,
            1,
            '24-hour check-in',
            24,
            'SMS',
            'Hi, this is your care team checking in after your discharge. Reply if you need support.',
            TRUE
        )
        ON CONFLICT (campaign_id, step_order) DO NOTHING;

        INSERT INTO outreach_events (
            outreach_event_id, patient_id, episode_id, campaign_id, workflow_id, channel,
            event_type, delivery_status, scheduled_at
        )
        VALUES (
            899101,
            810001,
            830001,
            898001,
            899001,
            'SMS',
            'SCHEDULED',
            'PENDING',
            CURRENT_TIMESTAMP
        )
        ON CONFLICT (outreach_event_id) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM outreach_events WHERE outreach_event_id = 899101")
    op.execute("DELETE FROM outreach_workflows WHERE workflow_id = 899001")
    op.execute("DELETE FROM outreach_campaigns WHERE campaign_id = 898001")
    op.execute("DELETE FROM escalation_actions WHERE escalation_action_id = 897001")
    op.execute("DELETE FROM escalation_assignments WHERE assignment_id = 896001")
    op.execute("DELETE FROM escalations WHERE escalation_id = 895001")
    op.execute("DELETE FROM queue_memberships WHERE queue_membership_id = 890101")
    op.execute("DELETE FROM care_team_queues WHERE queue_id = 890001")
    op.execute("DELETE FROM conversation_guardrail_hits WHERE guardrail_hit_id = 880101")
    op.execute("DELETE FROM clinical_guardrail_rules WHERE rule_id = 870001")
    op.execute("DELETE FROM clinical_guardrail WHERE guardrail_id = 860001")
    op.execute("DELETE FROM conversation_messages WHERE message_id = 850001")
    op.execute("DELETE FROM conversation_threads WHERE thread_id = 840001")
    op.execute("DELETE FROM care_navigation_episodes WHERE episode_id = 830001")
    op.execute("DELETE FROM patient_enrollments WHERE enrollment_id = 820001")
    op.execute("DELETE FROM patient_profiles WHERE patient_id IN (810001, 810002, 810003)")
    op.execute("DELETE FROM staff_profiles WHERE staff_id = 880001")
    op.execute("DELETE FROM users WHERE user_id IN (990001, 910001, 910002, 910003)")
    op.execute("DELETE FROM users WHERE email = 'demo.admin@patientai.local'")
    op.execute("DELETE FROM organizations WHERE organization_name = 'Patient AI Demo Org'")
