

## 1. Required tables

### A. Organization, authentication and profiles

| No. | Table              | Purpose                                                                                      |
| --- | ------------------ | -------------------------------------------------------------------------------------------- |
| 1   | `organizations`    | Stores hospitals or healthcare organizations using the application.                          |
| 2   | `roles`            | Defines roles such as Patient, Nurse, Pharmacist and Care Manager.                           |
| 3   | `users`            | Stores login accounts, credentials and account status.                                       |
| 4   | `patient_profiles` | Maps application patients to their FHIR Patient IDs and stores minimal app-specific details. |
| 5   | `staff_profiles`   | Stores staff details, departments and professional information needed by the application.    |

### B. Consent and care episodes

| No. | Table                      | Purpose                                                               |
| --- | -------------------------- | --------------------------------------------------------------------- |
| 6   | `patient_consent_records`  | Stores AI disclosure, outreach consent and revocation history.        |
| 7   | `patient_enrollments`      | Tracks enrollment in programs such as TCM, if required by your pilot. |
| 8   | `care_navigation_episodes` | Tracks each care workflow, such as a 30-day post-discharge episode.   |

### C. Conversation and AI safety

| No. | Table                              | Purpose                                                                          |
| --- | ---------------------------------- | -------------------------------------------------------------------------------- |
| 9   | `conversation_threads`             | Stores one record per conversation session.                                      |
| 10  | `conversation_messages`            | Stores each patient, AI, staff or system message in a separate row.              |
| 11  | `clinical_guardrail_rules`         | Stores clinical safety rule definitions.                                         |
| 12  | `clinical_guardrail_rule_versions` | Maintains approved versions of safety rules.                                     |
| 13  | `conversation_guardrail_hits`      | Records which safety rule was triggered, by which message, and the action taken. |
| 14  | `emergency_events`                 | Records emergency-level events and emergency response actions.                   |

### D. Care-team escalation and resolution

| No. | Table                    | Purpose                                                            |
| --- | ------------------------ | ------------------------------------------------------------------ |
| 15  | `care_team_queues`       | Defines nurse, pharmacist and care-manager work queues.            |
| 16  | `queue_memberships`      | Maps staff members to the queues they can handle.                  |
| 17  | `escalations`            | Stores clinical or operational cases requiring human attention.    |
| 18  | `escalation_assignments` | Tracks who owns an escalation and changes in assignment.           |
| 19  | `escalation_actions`     | Records calls, reviews, follow-up attempts and resolution actions. |

### E. Outreach and follow-up

| No. | Table                   | Purpose                                                                   |
| --- | ----------------------- | ------------------------------------------------------------------------- |
| 20  | `outreach_campaigns`    | Defines reusable outreach campaigns, if scheduled outreach is in the MVP. |
| 21  | `outreach_workflows`    | Defines steps, timing, channels and response rules for campaigns.         |
| 22  | `outreach_events`       | Records actual messages sent, delivery status and patient responses.      |

### F. Security and integration operations

| No. | Table                     | Purpose                                                                           |
| --- | ------------------------- | --------------------------------------------------------------------------------- |
| 25  | `audit_logs`              | Records sensitive access and important application actions.                       |


## 3. Recommended implementation order

1. Foundation: organizations, roles, users, patient profiles and staff profiles.
2. Patient workflows: consent records, enrollments and care-navigation episodes.
3. Conversation: threads and messages.
4. Safety: guardrail rules, versions, guardrail hits and emergency events.
5. Human intervention: queues, memberships, escalations, assignments and actions.
6. Automation: outreach tables and TCM tracking, if required for the pilot.
7. Operations: audit logs and integration sync tables, where the application owns the integration process.

---

Let's take two scenarios where a patient sends a message. In Scenario 1, an escalation is created, while in Scenario 2, no escalation is created.

## Scenario 1: Human escalation is created

Patient message: “I feel dizzy after taking my medication. Should I stop taking it?”

The system detects a medication-safety concern, avoids giving medication-change advice, and routes the case to a human for review.

1\. `conversation_threads`

Populated if this is a new conversation; otherwise, the existing thread is reused.

2\. `conversation_messages`

Stores the patient's message and the AI's safe response.

3\. `conversation_guardrail_hits`

Stores the triggered medication-safety rule, severity, reason, and action taken.

4\. `escalations`

Creates the human-review case, including its urgency, status, and assigned queue.

5\. `care_team_queues` and optionally `queue_memberships`

The existing queue is used for routing; queue membership identifies eligible staff if your application uses it.

6\. Assignment and action records

`escalation_assignments` records the assignment if you retain that table. `escalation_actions` records staff actions, contact attempts, outcomes, and resolution.

7\. `audit_logs`

Records relevant auditable events, such as escalation creation, assignment, or resolution, according to your audit policy.

Flow: Patient message → Guardrail hit → Safe AI response → Escalation created → Human reviews and documents the outcome.

## Scenario 2: No human escalation is created

Patient message: “Can you explain the discharge instructions my doctor gave me?”

The AI explains the available discharge instructions using approved patient context. No safety rule is triggered, and human intervention is not needed.

1\. `conversation_threads`

Creates a thread if needed; otherwise, reuses the existing one.

2\. `conversation_messages`

Stores the patient's question and the AI's response.

3\. `clinical_guardrail` / `clinical_guardrail_rules`

The system may consult the Markdown guidance and applicable rules, but no row is inserted into `conversation_guardrail_hits` if no rule is triggered.

4\. `audit_logs` — if required

A conversation or AI-response event may be logged according to your audit policy. It is not necessarily a separate audit entry for every message.

Flow: Patient message → Check applicable guardrails → AI responds safely → Conversation continues.

No rows are created in `escalations`, `escalation_assignments`, or `escalation_actions` because no escalation or staff action occurred.


---

### What happens for each user message? (Scenario on what case what are all the table has to be populated)

| Table                         | Safe message                 | Guardrail triggered                           |
| ----------------------------- | ---------------------------- | --------------------------------------------- |
| `conversation_messages`       | Insert                       | Insert                                        |
| `clinical_guardrail`          | Read applicable guidance     | Read applicable guidance                      |
| `clinical_guardrail_rules`    | Check applicable rules       | Check applicable rules                        |
| `conversation_guardrail_hits` | No insert if no rule matches | Insert a record for each triggered rule       |
| `escalations`                 | No insert                    | Insert only if human intervention is required |
| `escalation_actions`          | No insert                    | Insert when staff takes action                |

### Example 1: Safe message

Patient: “What time is my follow-up appointment?”

1. Store the message in `conversation_messages`.
2. Check the applicable rules and patient context.
3. AI provides the appointment information.
4. No guardrail is triggered, so no `conversation_guardrail_hits` row is created.
5. No escalation is created.

### Example 2: Guardrail triggered, but no escalation

Patient: “Can you diagnose my headache?”

1. Store the message in `conversation_messages`.
2. A diagnosis-related rule matches.
3. Insert a row into `conversation_guardrail_hits`.
4. AI declines to diagnose and provides an approved safe response.
5. No escalation is created unless the configured policy requires human review.

### Example 3: Guardrail triggered and escalation created

Patient: “I feel dizzy after taking my medication. Should I stop it?”

1. Store the message in `conversation_messages`.
2. A medication-safety rule matches.
3. Insert a row into `conversation_guardrail_hits`.
4. Provide a safe response and create an `escalations` record if the workflow requires human review.
5. Record staff actions in `escalation_actions` when they occur.

Remember this rule:

- `conversation_messages` → every user and AI message.
- `clinical_guardrail` and `clinical_guardrail_rules` → configuration and guidance that the application reads; not new rows per message.
- `conversation_guardrail_hits` → only when a rule actually triggers.
- `escalations` → only when human intervention is required.
- `escalation_actions` → when staff takes action.

---

2. Who creates and runs the campaign?

Human — configures the campaign
An authorized care manager or administrator configures the campaign, target patients, workflow schedule, message templates, and escalation rules. Clinical staff approve clinical content where needed.




System — executes it automatically
The application identifies eligible patients, schedules outreach, sends messages through the configured channel, records delivery and responses, and schedules the next step when appropriate.




Human care team — handles exceptions
Nurses, pharmacists, or care managers handle cases that need human intervention, such as medication concerns, worsening symptoms, or unresolved follow-up needs.

---


##  How it works

TABLE 1

`outreach_campaigns` — What is the plan?

Post-Discharge Follow-up

TABLE 2

`outreach_workflows` — When should it run?

- 24 hours after discharge: First check-in
- Day 7: Recovery follow-up
- Day 14: Follow-up confirmation

SYSTEM EXECUTES THE SCHEDULE

`outreach_events` — What happened?

Records the patient-specific scheduled activity, whether it was sent or delivered, and whether the patient responded.
