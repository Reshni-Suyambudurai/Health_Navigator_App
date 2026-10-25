# Patient AI Health Navigator Table Guide (DBML Aligned)

This document is aligned to [patient_ai_health_navigator_Schema_DBMLd.dbml](patient_ai_health_navigator_Schema_DBMLd.dbml).
For each table:
- Purpose: Why the table exists.
- Example record: One realistic row.

## Core Identity and Organization

### organizations
Purpose: Master list of participating healthcare organizations.

Example record:
```json
{
  "organization_id": 101,
  "organization_name": "CityCare Health System",
  "organization_type": "HOSPITAL",
  "npi_number": "1234567890",
  "address": "1200 Main St, Dallas, TX",
  "phone": "+1-214-555-0100",
  "status": "ACTIVE",
  "created_at": "2026-10-01T09:00:00Z",
  "updated_at": "2026-10-15T16:20:00Z"
}
```

### roles
Purpose: Defines role catalog used by users and workflow routing.

Example record:
```json
{
  "role_id": 6,
  "role_name": "PHARMACIST",
  "description": "Medication-related escalations",
  "created_at": "2026-09-20T10:00:00Z"
}
```

### users
Purpose: Login/user identity table for patients and staff.

Example record:
```json
{
  "user_id": 5001,
  "organization_id": 101,
  "role_id": 6,
  "first_name": "Emma",
  "last_name": "Williams",
  "email": "emma.williams@citycare.org",
  "password_hash": "$2b$12$...",
  "phone": "+1-214-555-0199",
  "status": "ACTIVE",
  "is_verified": true,
  "last_login_at": "2026-10-17T08:12:00Z",
  "created_at": "2026-09-20T10:10:00Z",
  "updated_at": "2026-10-17T08:12:00Z"
}
```

### patient_profiles
Purpose: Patient demographic and preference profile linked to a user.

Example record:
```json
{
  "patient_id": 9001,
  "user_id": 7001,
  "external_fhir_patient_id": "FHIR-2310",
  "date_of_birth": "1958-02-11",
  "gender": "MALE",
  "preferred_language": "en-US",
  "preferred_contact_method": "SMS",
  "emergency_contact_name": "Linda Brown",
  "emergency_contact_phone": "+1-469-555-1010",
  "risk_tier": "HIGH",
  "created_at": "2026-10-01T10:00:00Z",
  "updated_at": "2026-10-14T15:30:00Z"
}
```

### staff_profiles
Purpose: Staff-specific operational profile linked to a user.

Example record:
```json
{
  "staff_id": 3001,
  "user_id": 5001,
  "employee_id": "EMP-0021",
  "license_number": "PHARM-984433",
  "license_type": "PHARMACIST",
  "department": "Care Navigation",
  "specialization": "Cardiology Med Management",
  "created_at": "2026-09-20T10:20:00Z",
  "updated_at": "2026-10-10T12:00:00Z"
}
```

## Consent, Enrollment, and Episodes

### patient_consent_records
Purpose: Tracks AI and outreach consent lifecycle per patient.

Example record:
```json
{
  "consent_id": 11001,
  "patient_id": 9001,
  "consent_type": "AI_DISCLOSURE",
  "consent_status": "ACCEPTED",
  "consent_text_version": "v1.2",
  "effective_at": "2026-10-01T10:05:00Z",
  "revoked_at": null,
  "captured_channel": "PORTAL",
  "captured_by_user_id": 7001,
  "created_at": "2026-10-01T10:05:01Z"
}
```

### patient_enrollments
Purpose: Enrollment of patients into specific care-management programs.

Example record:
```json
{
  "enrollment_id": 13001,
  "patient_id": 9001,
  "organization_id": 101,
  "enrollment_program": "TCM",
  "enrollment_status": "ACTIVE",
  "enrollment_date": "2026-10-02T09:20:00Z",
  "close_date": null,
  "closed_reason": null,
  "created_by_user_id": 5001,
  "created_at": "2026-10-02T09:20:10Z",
  "updated_at": "2026-10-02T09:20:10Z"
}
```

### care_navigation_episodes
Purpose: Case-style timeline of a patient navigation episode.

Example record:
```json
{
  "episode_id": 14001,
  "patient_id": 9001,
  "enrollment_id": 13001,
  "episode_type": "POST_DISCHARGE_30_DAY",
  "trigger_type": "DISCHARGE",
  "trigger_reference": "enc-887122",
  "status": "OPEN",
  "opened_at": "2026-10-02T10:00:00Z",
  "closed_at": null,
  "owner_staff_id": 3001,
  "created_at": "2026-10-02T10:00:00Z",
  "updated_at": "2026-10-02T10:00:00Z"
}
```

## Conversation and Guardrails

### conversation_threads
Purpose: Container for one patient conversation session.

Example record:
```json
{
  "thread_id": 17001,
  "patient_id": 9001,
  "episode_id": 14001,
  "channel": "SMS",
  "language": "en-US",
  "started_at": "2026-10-17T08:15:00Z",
  "ended_at": null,
  "status": "ACTIVE",
  "created_at": "2026-10-17T08:15:00Z"
}
```

### conversation_messages
Purpose: Stores each message in a thread, including AI metadata and intent.

Example record:
```json
{
  "message_id": 19001,
  "thread_id": 17001,
  "sender_type": "AI",
  "sender_user_id": null,
  "ai_model_name": "gpt-5.3-codex",
  "ai_model_version": "2026-10",
  "message_text": "I understand your concern. I will connect you to your care team today.",
  "message_intent": "MEDICATION_CONCERN",
  "readability_grade": 7,
  "is_guardrail_override": false,
  "message_metadata": {"tone": "supportive"},
  "sent_at": "2026-10-17T08:15:12Z"
}
```

### clinical_guardrail
Purpose: High-level guardrail artifact (human-readable guidance set).

Example record:
```json
{
  "guardrail_id": 21001,
  "guardrail_name": "Medication Safety Guardrails",
  "guardrail_markdown": "Do not provide dose change instructions; escalate to licensed staff.",
  "created_at": "2026-09-30T12:00:00Z",
  "updated_at": "2026-10-10T09:00:00Z"
}
```

### clinical_guardrail_rules
Purpose: Deterministic operational rules linked to a guardrail set.

Example record:
```json
{
  "rule_id": 22001,
  "guardrail_id": 21001,
  "rule_name": "Medication stop request",
  "rule_category": "MEDICATION",
  "urgency_level": "SAME_DAY",
  "handler_role_id": 6,
  "action_type": "ESCALATE",
  "status": "ACTIVE",
  "created_at": "2026-10-01T08:00:00Z",
  "updated_at": "2026-10-12T11:00:00Z"
}
```

### conversation_guardrail_hits
Purpose: Fact table of rule triggers in live conversation.

Example record:
```json
{
  "guardrail_hit_id": 23001,
  "thread_id": 17001,
  "message_id": 19001,
  "patient_id": 9001,
  "rule_id": 22001,
  "hit_urgency_level": "SAME_DAY",
  "action_taken": "ESCALATE",
  "hit_reason": "Patient asked to stop carvedilol due to dizziness",
  "created_at": "2026-10-17T08:15:14Z"
}
```

### emergency_events
Purpose: Dedicated tracking for emergency-level detections and actions.

Example record:
```json
{
  "emergency_event_id": 24001,
  "patient_id": 9002,
  "thread_id": 17120,
  "guardrail_hit_id": 23077,
  "emergency_type": "CHEST_PAIN",
  "emergency_instruction_sent": true,
  "notified_care_team": true,
  "event_status": "ESCALATED",
  "detected_at": "2026-10-17T07:40:00Z",
  "resolved_at": null,
  "created_at": "2026-10-17T07:40:01Z"
}
```

## Care-Team Queue and Escalation Workflow

### care_team_queues
Purpose: Queue definitions used to route escalations.

Example record:
```json
{
  "queue_id": 25001,
  "organization_id": 101,
  "queue_name": "TCM Nurse Queue",
  "queue_type": "NURSE",
  "sla_minutes": 60,
  "status": "ACTIVE",
  "created_at": "2026-10-01T07:00:00Z"
}
```

### queue_memberships
Purpose: Staff membership and role within a queue.

Example record:
```json
{
  "queue_membership_id": 26001,
  "queue_id": 25001,
  "staff_id": 3001,
  "role_in_queue": "PRIMARY",
  "is_active": true,
  "created_at": "2026-10-01T07:05:00Z"
}
```

### escalations
Purpose: Main escalation case record.

Example record:
```json
{
  "escalation_id": 27001,
  "patient_id": 9001,
  "episode_id": 14001,
  "thread_id": 17001,
  "guardrail_hit_id": 23001,
  "queue_id": 25001,
  "escalation_type": "MEDICATION",
  "priority": "HIGH",
  "reason": "Medication stop request",
  "patient_summary": "HF patient dizzy after carvedilol",
  "status": "OPEN",
  "created_at": "2026-10-17T08:15:15Z",
  "resolved_at": null
}
```

### escalation_assignments
Purpose: Tracks who owns escalation handling and when ownership changes.

Example record:
```json
{
  "assignment_id": 28001,
  "escalation_id": 27001,
  "assigned_to_staff_id": 3001,
  "assigned_by_user_id": 5001,
  "assigned_at": "2026-10-17T08:16:00Z",
  "unassigned_at": null,
  "is_active": true
}
```

### escalation_actions
Purpose: Timeline of actions taken while resolving an escalation.

Example record:
```json
{
  "escalation_action_id": 29001,
  "escalation_id": 27001,
  "action_by_user_id": 5001,
  "action_type": "PATIENT_CONTACTED",
  "action_notes": "Explained symptoms and arranged same-day nurse callback",
  "action_at": "2026-10-17T08:30:00Z"
}
```

## Outreach Automation

### outreach_campaigns
Purpose: Reusable outreach program definition.

Example record:
```json
{
  "campaign_id": 30001,
  "organization_id": 101,
  "campaign_name": "HF Post-Discharge 30 Day",
  "campaign_type": "POST_DISCHARGE",
  "target_cohort_definition": {"episode_type": "POST_DISCHARGE_30_DAY", "risk_tier": ["HIGH", "CRITICAL"]},
  "status": "ACTIVE",
  "created_by_user_id": 5001,
  "created_at": "2026-10-01T08:00:00Z",
  "updated_at": "2026-10-10T08:00:00Z"
}
```

### outreach_workflows
Purpose: Ordered campaign steps with timing/channel/template.

Example record:
```json
{
  "workflow_id": 31001,
  "campaign_id": 30001,
  "step_order": 1,
  "step_name": "24h check-in",
  "trigger_offset_hours": 24,
  "channel": "SMS",
  "template_text": "How are you feeling after discharge today?",
  "escalation_on_no_response": true,
  "created_at": "2026-10-01T08:05:00Z"
}
```

### outreach_events
Purpose: Execution log of patient-level outreach events.

Example record:
```json
{
  "outreach_event_id": 32001,
  "patient_id": 9001,
  "episode_id": 14001,
  "campaign_id": 30001,
  "workflow_id": 31001,
  "channel": "SMS",
  "event_type": "CHECKIN_SENT",
  "delivery_status": "DELIVERED",
  "scheduled_at": "2026-10-03T10:00:00Z",
  "sent_at": "2026-10-03T10:00:05Z",
  "responded_at": "2026-10-03T10:12:10Z",
  "created_at": "2026-10-03T10:00:05Z"
}
```

## Audit and Compliance Traceability

### audit_logs
Purpose: Immutable security/compliance audit trail for sensitive operations.

Example record:
```json
{
  "audit_id": 33001,
  "user_id": 5001,
  "patient_id": 9001,
  "action": "READ",
  "resource_type": "ESCALATION",
  "resource_id": "27001",
  "details": {"screen": "EscalationDetail", "reason": "triage"},
  "ip_address": "10.20.3.44",
  "correlation_id": "req-6f2b0c39",
  "created_at": "2026-10-17T08:16:05Z"
}
```

## Notes

- This file documents only tables that exist in [patient_ai_health_navigator_Schema_DBMLd.dbml](patient_ai_health_navigator_Schema_DBMLd.dbml).
- Enum-like fields are shown as practical values from DBML comments.
- Example data is illustrative and safe for documentation use.
