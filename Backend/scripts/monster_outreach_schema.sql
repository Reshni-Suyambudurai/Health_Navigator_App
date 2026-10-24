-- Run against the Navigator/application PostgreSQL database, not the read-only
-- PatientFHIR source. This script is rerunnable and intentionally replaces an
-- Alembic migration for the outreach/check-in feature set.

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'campaign_type') THEN
        CREATE TYPE campaign_type AS ENUM (
            'POST_DISCHARGE', 'CHRONIC_CARE', 'MEDICATION_FOLLOWUP',
            'MEDICATION_ADHERENCE', 'APPOINTMENT_REMINDER', 'HEALTH_EDUCATION',
            'SATISFACTION_SURVEY', 'CHECK_IN', 'FOLLOW_UP'
        );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'campaign_status') THEN
        CREATE TYPE campaign_status AS ENUM ('DRAFT', 'ACTIVE', 'PAUSED', 'COMPLETED', 'ARCHIVED');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'outreach_channel') THEN
        CREATE TYPE outreach_channel AS ENUM ('SMS', 'CALL', 'PHONE', 'EMAIL', 'PORTAL');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'outreach_event_channel') THEN
        CREATE TYPE outreach_event_channel AS ENUM ('SMS', 'CALL', 'PHONE', 'EMAIL', 'PORTAL');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'outreach_event_type') THEN
        CREATE TYPE outreach_event_type AS ENUM (
            'CHECK_IN', 'APPOINTMENT_REMINDER', 'REFILL_REMINDER', 'FOLLOW_UP',
            'SENT', 'DELIVERED', 'OPENED', 'REPLIED', 'FAILED', 'SCHEDULED'
        );
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'delivery_status') THEN
        CREATE TYPE delivery_status AS ENUM ('PENDING', 'SENT', 'DELIVERED', 'FAILED', 'RESPONDED');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'appointment_type') THEN
        CREATE TYPE appointment_type AS ENUM ('POST_DISCHARGE', 'NURSE_FOLLOWUP', 'CARE_MANAGER_CALL');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'appointment_status') THEN
        CREATE TYPE appointment_status AS ENUM (
            'REQUESTED', 'SCHEDULED', 'CONFIRMED', 'COMPLETED',
            'CANCELLED', 'NO_SHOW', 'RESCHEDULED'
        );
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'booking_method') THEN
        CREATE TYPE booking_method AS ENUM ('STAFF', 'PATIENT_PORTAL', 'EHR_INTEGRATION');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'outreach_trigger_type') THEN
        CREATE TYPE outreach_trigger_type AS ENUM ('AFTER_DISCHARGE', 'BEFORE_APPOINTMENT', 'AFTER_EVENT');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'outreach_trigger_anchor') THEN
        CREATE TYPE outreach_trigger_anchor AS ENUM ('DISCHARGE_DATETIME', 'APPOINTMENT_DATETIME', 'EVENT_DATETIME');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'checkin_template_type') THEN
        CREATE TYPE checkin_template_type AS ENUM ('POST_DISCHARGE', 'CHRONIC_CARE', 'MEDICATION_FOLLOWUP');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'checkin_template_status') THEN
        CREATE TYPE checkin_template_status AS ENUM ('DRAFT', 'ACTIVE', 'INACTIVE');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'checkin_answer_type') THEN
        CREATE TYPE checkin_answer_type AS ENUM ('YES_NO', 'TEXT', 'NUMBER', 'SINGLE_CHOICE', 'MULTIPLE_CHOICE');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'checkin_session_status') THEN
        CREATE TYPE checkin_session_status AS ENUM ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'ABANDONED', 'ESCALATED');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'checkin_response_source') THEN
        CREATE TYPE checkin_response_source AS ENUM ('PATIENT_REPORTED', 'STAFF_ENTERED');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'appointment_contact_method') THEN
        CREATE TYPE appointment_contact_method AS ENUM ('PHONE', 'PORTAL', 'SMS', 'VIDEO', 'IN_PERSON', 'INTERNAL_REVIEW');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'appointment_action_type') THEN
        CREATE TYPE appointment_action_type AS ENUM ('REVIEWED', 'CALL_ATTEMPT', 'PATIENT_CONTACTED', 'GUIDANCE_PROVIDED', 'REFERRED', 'OTHER');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'appointment_outcome') THEN
        CREATE TYPE appointment_outcome AS ENUM ('REACHED', 'NO_ANSWER', 'ISSUE_ADDRESSED', 'ISSUE_UNRESOLVED', 'REFERRED', 'OTHER');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'appointment_resolution_status') THEN
        CREATE TYPE appointment_resolution_status AS ENUM ('PENDING', 'RESOLVED', 'FOLLOW_UP_REQUIRED', 'UNABLE_TO_REACH');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'follow_up_task_type') THEN
        CREATE TYPE follow_up_task_type AS ENUM ('PATIENT_CONTACT', 'MEDICATION_FOLLOWUP', 'APPOINTMENT_BOOKING', 'CLINICAL_REVIEW', 'OTHER');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'follow_up_priority') THEN
        CREATE TYPE follow_up_priority AS ENUM ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'follow_up_task_status') THEN
        CREATE TYPE follow_up_task_status AS ENUM ('OPEN', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED');
    END IF;
END $$;

ALTER TYPE campaign_type ADD VALUE IF NOT EXISTS 'POST_DISCHARGE';
ALTER TYPE campaign_type ADD VALUE IF NOT EXISTS 'CHRONIC_CARE';
ALTER TYPE campaign_type ADD VALUE IF NOT EXISTS 'MEDICATION_FOLLOWUP';
ALTER TYPE outreach_channel ADD VALUE IF NOT EXISTS 'PHONE';
ALTER TYPE outreach_event_channel ADD VALUE IF NOT EXISTS 'PHONE';
ALTER TYPE outreach_event_type ADD VALUE IF NOT EXISTS 'CHECK_IN';
ALTER TYPE outreach_event_type ADD VALUE IF NOT EXISTS 'APPOINTMENT_REMINDER';
ALTER TYPE outreach_event_type ADD VALUE IF NOT EXISTS 'REFILL_REMINDER';
ALTER TYPE outreach_event_type ADD VALUE IF NOT EXISTS 'FOLLOW_UP';
ALTER TYPE delivery_status ADD VALUE IF NOT EXISTS 'RESPONDED';

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'outreach_event_status') THEN
        CREATE TYPE outreach_event_status AS ENUM (
            'PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'CANCELLED'
        );
    END IF;
END $$;

BEGIN;

ALTER TABLE outreach_campaigns
    ALTER COLUMN campaign_name TYPE varchar(255),
    ADD COLUMN IF NOT EXISTS timezone varchar(100) NOT NULL DEFAULT 'UTC',
    ADD COLUMN IF NOT EXISTS start_at timestamp,
    ADD COLUMN IF NOT EXISTS end_at timestamp,
    ADD COLUMN IF NOT EXISTS updated_by_user_id bigint,
    ADD COLUMN IF NOT EXISTS updated_at timestamp DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE outreach_campaigns
    ALTER COLUMN status SET DEFAULT 'DRAFT';

DO $$
DECLARE
    fallback_user_id bigint;
BEGIN
    IF EXISTS (SELECT 1 FROM outreach_campaigns WHERE created_by_user_id IS NULL) THEN
        SELECT user_id INTO fallback_user_id FROM users ORDER BY user_id LIMIT 1;
        IF fallback_user_id IS NULL THEN
            RAISE EXCEPTION 'Cannot backfill outreach_campaigns.created_by_user_id without an existing user';
        END IF;
        UPDATE outreach_campaigns SET created_by_user_id = fallback_user_id WHERE created_by_user_id IS NULL;
    END IF;
    ALTER TABLE outreach_campaigns ALTER COLUMN created_by_user_id SET NOT NULL;
    ALTER TABLE outreach_campaigns DROP CONSTRAINT IF EXISTS outreach_campaigns_created_by_user_id_fkey;
    ALTER TABLE outreach_campaigns ADD CONSTRAINT outreach_campaigns_created_by_user_id_fkey
        FOREIGN KEY (created_by_user_id) REFERENCES users(user_id) ON DELETE RESTRICT;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'outreach_campaigns_updated_by_user_id_fkey') THEN
        ALTER TABLE outreach_campaigns ADD CONSTRAINT outreach_campaigns_updated_by_user_id_fkey
            FOREIGN KEY (updated_by_user_id) REFERENCES users(user_id) ON DELETE SET NULL;
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS checkin_templates (
    checkin_template_id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    organization_id bigint NOT NULL REFERENCES organizations(organization_id) ON DELETE RESTRICT,
    template_name varchar(255) NOT NULL,
    template_type checkin_template_type NOT NULL,
    description text,
    version integer NOT NULL DEFAULT 1,
    status checkin_template_status NOT NULL DEFAULT 'DRAFT',
    created_by_user_id bigint NOT NULL REFERENCES users(user_id) ON DELETE RESTRICT,
    created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_checkin_templates_org_name_version
        UNIQUE (organization_id, template_name, version)
);

CREATE INDEX IF NOT EXISTS ix_checkin_templates_status
    ON checkin_templates (status);

CREATE TABLE IF NOT EXISTS checkin_questions (
    question_id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    checkin_template_id bigint NOT NULL REFERENCES checkin_templates(checkin_template_id) ON DELETE CASCADE,
    question_key varchar(100) NOT NULL,
    question_text text NOT NULL,
    answer_type checkin_answer_type NOT NULL,
    options json,
    display_order integer NOT NULL,
    is_required boolean NOT NULL DEFAULT true,
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_checkin_questions_template_key UNIQUE (checkin_template_id, question_key),
    CONSTRAINT uq_checkin_questions_template_order UNIQUE (checkin_template_id, display_order),
    CONSTRAINT chk_question_display_order CHECK (display_order > 0)
);

ALTER TABLE outreach_workflows
    ALTER COLUMN step_name TYPE varchar(255),
    ADD COLUMN IF NOT EXISTS trigger_type outreach_trigger_type,
    ADD COLUMN IF NOT EXISTS trigger_anchor outreach_trigger_anchor,
    ADD COLUMN IF NOT EXISTS checkin_template_id bigint,
    ADD COLUMN IF NOT EXISTS max_attempts integer NOT NULL DEFAULT 3,
    ADD COLUMN IF NOT EXISTS retry_interval_minutes integer NOT NULL DEFAULT 30,
    ADD COLUMN IF NOT EXISTS is_active boolean NOT NULL DEFAULT true,
    ADD COLUMN IF NOT EXISTS updated_at timestamp DEFAULT CURRENT_TIMESTAMP;

UPDATE outreach_workflows
SET trigger_type = COALESCE(trigger_type, 'AFTER_EVENT'),
    trigger_anchor = COALESCE(trigger_anchor, 'EVENT_DATETIME')
WHERE trigger_type IS NULL OR trigger_anchor IS NULL;

ALTER TABLE outreach_workflows
    ALTER COLUMN trigger_type SET NOT NULL,
    ALTER COLUMN trigger_anchor SET NOT NULL,
    ALTER COLUMN trigger_offset_hours SET DEFAULT 0,
    ALTER COLUMN template_text DROP NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'outreach_workflows_checkin_template_id_fkey') THEN
        ALTER TABLE outreach_workflows ADD CONSTRAINT outreach_workflows_checkin_template_id_fkey
            FOREIGN KEY (checkin_template_id) REFERENCES checkin_templates(checkin_template_id) ON DELETE SET NULL;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_workflow_step_order') THEN
        ALTER TABLE outreach_workflows ADD CONSTRAINT chk_workflow_step_order CHECK (step_order > 0);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_trigger_offset') THEN
        ALTER TABLE outreach_workflows ADD CONSTRAINT chk_trigger_offset CHECK (trigger_offset_hours >= 0);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_max_attempts') THEN
        ALTER TABLE outreach_workflows ADD CONSTRAINT chk_max_attempts CHECK (max_attempts > 0);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_retry_interval') THEN
        ALTER TABLE outreach_workflows ADD CONSTRAINT chk_retry_interval CHECK (retry_interval_minutes >= 0);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_outreach_workflows_checkin_template_id
    ON outreach_workflows (checkin_template_id);

ALTER TABLE outreach_events
    ALTER COLUMN episode_id DROP NOT NULL,
    ADD COLUMN IF NOT EXISTS appointment_id bigint,
    ADD COLUMN IF NOT EXISTS event_status outreach_event_status NOT NULL DEFAULT 'PENDING',
    ADD COLUMN IF NOT EXISTS completed_at timestamp,
    ADD COLUMN IF NOT EXISTS attempt_count integer NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS last_error text,
    ADD COLUMN IF NOT EXISTS idempotency_key varchar(255),
    ADD COLUMN IF NOT EXISTS updated_at timestamp DEFAULT CURRENT_TIMESTAMP;

UPDATE outreach_events
SET scheduled_at = COALESCE(scheduled_at, created_at),
    idempotency_key = COALESCE(idempotency_key, 'legacy-outreach-' || outreach_event_id::text);

ALTER TABLE outreach_events
    ALTER COLUMN scheduled_at SET NOT NULL,
    ALTER COLUMN delivery_status SET DEFAULT 'PENDING',
    ALTER COLUMN idempotency_key SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_outreach_events_idempotency_key') THEN
        ALTER TABLE outreach_events ADD CONSTRAINT uq_outreach_events_idempotency_key UNIQUE (idempotency_key);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_outreach_attempt_count') THEN
        ALTER TABLE outreach_events ADD CONSTRAINT chk_outreach_attempt_count CHECK (attempt_count >= 0);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_outreach_events_status_scheduled
    ON outreach_events (event_status, scheduled_at);
CREATE INDEX IF NOT EXISTS ix_outreach_events_patient_episode
    ON outreach_events (patient_id, episode_id);
CREATE INDEX IF NOT EXISTS ix_outreach_events_campaign_workflow
    ON outreach_events (campaign_id, workflow_id);
CREATE INDEX IF NOT EXISTS ix_outreach_events_appointment_id
    ON outreach_events (appointment_id);

ALTER TABLE appointments
    ADD COLUMN IF NOT EXISTS source_outreach_event_id bigint,
    ADD COLUMN IF NOT EXISTS cancellation_reason text,
    ADD COLUMN IF NOT EXISTS rescheduled_from_appointment_id bigint;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'appointments_source_outreach_event_id_fkey') THEN
        ALTER TABLE appointments ADD CONSTRAINT appointments_source_outreach_event_id_fkey
            FOREIGN KEY (source_outreach_event_id) REFERENCES outreach_events(outreach_event_id) ON DELETE SET NULL;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'appointments_rescheduled_from_appointment_id_fkey') THEN
        ALTER TABLE appointments ADD CONSTRAINT appointments_rescheduled_from_appointment_id_fkey
            FOREIGN KEY (rescheduled_from_appointment_id) REFERENCES appointments(appointment_id) ON DELETE SET NULL;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'outreach_events_appointment_id_fkey') THEN
        ALTER TABLE outreach_events ADD CONSTRAINT outreach_events_appointment_id_fkey
            FOREIGN KEY (appointment_id) REFERENCES appointments(appointment_id) ON DELETE SET NULL;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_appointment_time') THEN
        ALTER TABLE appointments ADD CONSTRAINT chk_appointment_time
            CHECK (appointment_datetime < end_datetime);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_appointments_source_outreach_event_id
    ON appointments (source_outreach_event_id);
CREATE INDEX IF NOT EXISTS ix_appointments_rescheduled_from_appointment_id
    ON appointments (rescheduled_from_appointment_id);
CREATE INDEX IF NOT EXISTS ix_appointments_staff_time_range
    ON appointments (staff_id, appointment_datetime, end_datetime);
CREATE INDEX IF NOT EXISTS ix_appointments_patient_datetime
    ON appointments (patient_id, appointment_datetime);

CREATE TABLE IF NOT EXISTS checkin_sessions (
    checkin_session_id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    patient_id bigint NOT NULL REFERENCES patient_profiles(patient_id) ON DELETE CASCADE,
    episode_id bigint REFERENCES care_navigation_episodes(episode_id) ON DELETE SET NULL,
    outreach_event_id bigint NOT NULL UNIQUE REFERENCES outreach_events(outreach_event_id) ON DELETE CASCADE,
    checkin_template_id bigint NOT NULL REFERENCES checkin_templates(checkin_template_id) ON DELETE RESTRICT,
    thread_id bigint REFERENCES conversation_threads(thread_id) ON DELETE SET NULL,
    session_status checkin_session_status NOT NULL DEFAULT 'PENDING',
    started_at timestamp,
    completed_at timestamp,
    created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_checkin_sessions_patient_episode
    ON checkin_sessions (patient_id, episode_id);
CREATE INDEX IF NOT EXISTS ix_checkin_sessions_status_created
    ON checkin_sessions (session_status, created_at);

CREATE TABLE IF NOT EXISTS checkin_responses (
    response_id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    checkin_session_id bigint NOT NULL REFERENCES checkin_sessions(checkin_session_id) ON DELETE CASCADE,
    question_id bigint NOT NULL REFERENCES checkin_questions(question_id) ON DELETE RESTRICT,
    message_id bigint REFERENCES conversation_messages(message_id) ON DELETE SET NULL,
    answer_text text,
    answer_value json,
    response_source checkin_response_source NOT NULL DEFAULT 'PATIENT_REPORTED',
    recorded_by_user_id bigint REFERENCES users(user_id) ON DELETE SET NULL,
    answered_at timestamp NOT NULL,
    created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_checkin_responses_session_question UNIQUE (checkin_session_id, question_id)
);

CREATE TABLE IF NOT EXISTS appointment_actions (
    appointment_action_id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    appointment_id bigint NOT NULL REFERENCES appointments(appointment_id) ON DELETE CASCADE,
    patient_id bigint NOT NULL REFERENCES patient_profiles(patient_id) ON DELETE CASCADE,
    episode_id bigint REFERENCES care_navigation_episodes(episode_id) ON DELETE SET NULL,
    action_by_user_id bigint NOT NULL REFERENCES users(user_id) ON DELETE RESTRICT,
    contact_datetime timestamp,
    contact_method appointment_contact_method,
    action_taken appointment_action_type NOT NULL,
    outcome appointment_outcome,
    action_notes text,
    resolution_status appointment_resolution_status NOT NULL DEFAULT 'PENDING',
    follow_up_required boolean NOT NULL DEFAULT false,
    follow_up_notes text,
    follow_up_due_at timestamp,
    created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_appointment_actions_appointment_created
    ON appointment_actions (appointment_id, created_at);
CREATE INDEX IF NOT EXISTS ix_appointment_actions_patient_episode
    ON appointment_actions (patient_id, episode_id);
CREATE INDEX IF NOT EXISTS ix_appointment_actions_resolution_due
    ON appointment_actions (resolution_status, follow_up_due_at);

CREATE TABLE IF NOT EXISTS follow_up_tasks (
    follow_up_task_id bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    patient_id bigint NOT NULL REFERENCES patient_profiles(patient_id) ON DELETE CASCADE,
    episode_id bigint REFERENCES care_navigation_episodes(episode_id) ON DELETE SET NULL,
    appointment_id bigint REFERENCES appointments(appointment_id) ON DELETE SET NULL,
    escalation_id bigint REFERENCES escalations(escalation_id) ON DELETE SET NULL,
    task_type follow_up_task_type NOT NULL,
    title varchar(255) NOT NULL,
    description text,
    assigned_to_staff_id bigint REFERENCES staff_profiles(staff_id) ON DELETE SET NULL,
    created_by_user_id bigint REFERENCES users(user_id) ON DELETE SET NULL,
    due_at timestamp,
    priority follow_up_priority NOT NULL DEFAULT 'MEDIUM',
    status follow_up_task_status NOT NULL DEFAULT 'OPEN',
    completed_by_user_id bigint REFERENCES users(user_id) ON DELETE SET NULL,
    completed_at timestamp,
    completion_notes text,
    created_at timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_follow_up_tasks_status_due
    ON follow_up_tasks (status, due_at);
CREATE INDEX IF NOT EXISTS ix_follow_up_tasks_assignee_status_due
    ON follow_up_tasks (assigned_to_staff_id, status, due_at);
CREATE INDEX IF NOT EXISTS ix_follow_up_tasks_patient_episode
    ON follow_up_tasks (patient_id, episode_id);

-- Seed reusable configuration data using the first organization and user in
-- the target application database. Operational patient rows are not fabricated.
DO $$
DECLARE
    seed_organization_id bigint;
    seed_user_id bigint;
    post_discharge_template_id bigint;
BEGIN
    SELECT organization_id INTO seed_organization_id FROM organizations ORDER BY organization_id LIMIT 1;
    SELECT user_id INTO seed_user_id FROM users ORDER BY user_id LIMIT 1;

    IF seed_organization_id IS NULL OR seed_user_id IS NULL THEN
        RAISE NOTICE 'Skipping check-in seeds: an organization and user are required';
        RETURN;
    END IF;

    INSERT INTO checkin_templates (
        organization_id, template_name, template_type, description, version,
        status, created_by_user_id
    ) VALUES (
        seed_organization_id, 'Post-discharge wellness check', 'POST_DISCHARGE',
        'Standard symptoms, medication, and follow-up check after discharge.',
        1, 'ACTIVE', seed_user_id
    ) ON CONFLICT (organization_id, template_name, version) DO NOTHING;

    SELECT checkin_template_id INTO post_discharge_template_id
    FROM checkin_templates
    WHERE organization_id = seed_organization_id
      AND template_name = 'Post-discharge wellness check'
      AND version = 1;

    INSERT INTO checkin_questions (
        checkin_template_id, question_key, question_text, answer_type,
        options, display_order, is_required, is_active
    ) VALUES
        (post_discharge_template_id, 'overall_wellbeing', 'How are you feeling today?',
         'SINGLE_CHOICE', '["Better", "About the same", "Worse"]'::json, 1, true, true),
        (post_discharge_template_id, 'new_symptoms', 'Have you developed any new or worsening symptoms?',
         'YES_NO', NULL, 2, true, true),
        (post_discharge_template_id, 'medication_access', 'Do you have access to all prescribed medications?',
         'YES_NO', NULL, 3, true, true),
        (post_discharge_template_id, 'additional_notes', 'Is there anything else your care team should know?',
         'TEXT', NULL, 4, false, true)
    ON CONFLICT (checkin_template_id, question_key) DO NOTHING;
END $$;

COMMIT;