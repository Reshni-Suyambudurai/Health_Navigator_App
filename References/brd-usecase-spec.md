# Patient AI Health Navigator --- BRD / Use-Case Specification

**Portfolio:** KANINI Vertical Use Case Portfolio 2026\
**Use Case:** HC-03 --- Healthcare / Provider Patient Engagement\
**Version:** 1.0\
**Date in source:** September 2026\
**Target geography:** United States\
**Document type:** Vertical Use Case --- Business Challenge & Market
Assessment

> This document is a consolidated engineering/business specification
> derived from the BRD. It preserves the BRD's terminology, scope,
> constraints, metrics, risks, and use-case framing. Where the BRD does
> not specify an exact implementation value, this document does not
> invent one.

------------------------------------------------------------------------

## 1. Executive Summary

The Patient AI Health Navigator is a **between-visit care-navigation
assistant** operated under the brand of a health system, physician
group, or health plan. It can operate through SMS, web chat, patient
portal, and, in production, voice.

The navigator uses the patient's own record --- including conditions,
medications, discharge instructions, care plan, appointments, and
pharmacy-fill information --- to:

-   explain care information in plain language,
-   remind patients about medications and appointments,
-   check in after discharge,
-   identify refill gaps,
-   check understanding,
-   route clinically significant or out-of-scope issues to the
    appropriate human care team,
-   support transitional-care and other care-management workflows,
-   document relevant interactions and escalation activity.

The central design principle is:

**Structured patient data + deterministic clinical rules first; AI
assists with conversation.**

The LLM is responsible for natural-language conversation and
explanations. Deterministic rules decide what is allowed, when the AI
must stop, and when escalation or emergency instructions are required.

The navigator is **not** intended to diagnose, prescribe, change
medication doses, or interpret laboratory values.

------------------------------------------------------------------------

# 2. Business Problem

## 2.1 Core problem

The BRD identifies a major gap in healthcare between visits: patients
are expected to manage much of their own care with limited structured
support.

Patients may need to:

-   understand a new diagnosis,
-   take multiple medications correctly,
-   recognize warning signs,
-   attend follow-up appointments,
-   decide where to seek help when symptoms occur,
-   manage chronic conditions between visits.

Most healthcare delivery is organized around appointments, while the
period between visits is comparatively unmanaged.

## 2.2 Problems faced by hospitals and care organizations

### 1. Medication non-adherence

Patients frequently do not take chronic-disease medications as
prescribed.

The BRD cites:

-   approximately **30--50%** of chronic-disease medications not taken
    as prescribed;
-   approximately **\$100B** in associated annual US healthcare services
    in commonly cited estimates;
-   a broader estimate of **\$528.4B** for all non-optimized
    prescription drug use;
-   disease-specific non-adherence costs of approximately
    **\$949--\$44,190 per patient per year**.

The business problem is not simply reminding patients. Organizations
need personalized, recurrent outreach tied to the patient's actual
regimen and refill behavior.

### 2. Readmissions and poor transitions

The BRD highlights:

-   **3.8M** adult 30-day all-cause readmissions in 2018;
-   approximately **14%** readmission rate;
-   approximately **\$15,200** average cost per readmission;
-   Medicare 30-day readmission rate of about **17 per 100 index
    stays**;
-   HRRP penalties of up to **3%** of Medicare base operating DRG
    payments.

The transition from hospital to home is therefore a high-value workflow.

### 3. Missed appointments

The BRD cites an average appointment no-show rate of approximately
**23%** and notes that many practices report rising no-shows.

Missed follow-up appointments weaken continuity of care and
transitional-care performance.

### 4. Misdirected acute care

A portion of emergency-department visits may be potentially manageable
through urgent-care or retail settings.

Patients often lack structured guidance between visits about what their
next appropriate step should be.

### 5. Health-literacy barriers

The BRD highlights low health literacy and the need for understandable,
personalized explanations.

The Navigator therefore targets approximately a **6th--8th grade reading
level**.

### 6. Care-team capacity

Nurse lines, care managers, and contact centers are expensive and
difficult to scale.

Adding an uncontrolled patient-message channel can simply move more work
into clinician inboxes.

The Navigator is intended to resolve appropriate questions automatically
while escalating clinically meaningful cases with structured context.

### 7. AI safety and liability

Unsupervised patient-facing AI creates significant safety concerns.

The BRD cites:

-   **7.1%** of unedited LLM patient-message drafts in one study being
    judged at risk of severe harm;
-   **0.6%** at risk of death;
-   acuity judgment as a major failure mode;
-   ECRI ranking misuse of AI chatbots as the **#1 health technology
    hazard for 2026**.

Therefore, a generic chatbot is explicitly not sufficient.

### 8. Weak evidence of outcome impact

The BRD notes that transition interventions can reduce readmissions, but
more recent effects are smaller and simple reminder bots are unlikely to
reproduce the strongest historical results.

The product therefore needs measurable outcomes rather than a
chatbot-only value proposition.

------------------------------------------------------------------------

# 3. Why Hospitals / Buyers Care

The BRD identifies several economic and regulatory drivers.

## 3.1 HRRP

Hospital Readmissions Reduction Program penalties are an important
financial driver.

The BRD reports:

-   FY2026: **240 hospitals (8.1%)** had HRRP penalties of 1% or more;
-   FY2025: **208 hospitals (7.0%)**;
-   from FY2027, Medicare Advantage beneficiaries are included in all
    six readmission measures.

## 3.2 TCM

Transitional Care Management supports structured post-discharge work.

TCM requires contact within the required post-discharge window and
follow-up within 7 or 14 days depending on the applicable code.

The Navigator is designed to support, document, and route this work ---
**not replace the required clinical staff contact**.

## 3.3 APCM

Advanced Primary Care Management provides recurring payment for
continuous, team-based primary care.

The BRD highlights:

-   G0556
-   G0557
-   G0558

and associated requirements such as 24/7 access, continuity, digital
communication, and timely follow-up.

## 3.4 RPM

Remote Physiologic Monitoring supports monitoring of patient physiologic
information such as weight and other measurements.

The BRD discusses newer short-duration RPM codes and their potential
relationship to between-visit care.

## 3.5 CMS ACCESS

The CMS ACCESS model began July 5, 2026 and provides outcome-aligned
payments for technology-supported chronic care.

Heart failure and COPD tracks are identified as starting in 2027.

## 3.6 Part D adherence

The BRD highlights PQA adherence measures for:

-   diabetes medications,
-   renin-angiotensin-system antagonists,
-   statins.

This creates a payer incentive for adherence-focused navigation.

------------------------------------------------------------------------

# 4. Product Vision

## 4.1 What we are building

A **record-grounded, governed AI care-navigation layer** that operates
between visits.

It should:

1.  Know the patient's relevant clinical context.
2.  Answer questions using the patient's actual record.
3.  Ground education in trusted medical sources.
4.  Proactively reach out at appropriate events.
5.  Detect safety triggers using deterministic rules.
6.  Escalate to human care teams.
7.  Document the interaction.
8.  Support measurable care-management outcomes.

## 4.2 What the product is not

The Navigator must not:

-   diagnose,
-   prescribe,
-   change medication doses,
-   advise a patient to stop a medication,
-   independently interpret laboratory values,
-   operate as an unrestricted symptom-triage system,
-   replace licensed clinical staff where human contact is required.

The intended scope is:

**Education + navigation + reminders + monitoring/check-ins +
escalation.**

------------------------------------------------------------------------

# 5. Target Customers and Buyers

## Primary economic buyers

The BRD identifies:

-   Health-system Chief Digital / Chief Experience Officer
-   VP Population Health
-   VP Care Management
-   CMO / CNO for transitions-of-care programs
-   Payer VP Care Management / Stars
-   Value-based-care executives at ACOs and large physician groups

## Primary users

-   Patients
-   Caregivers
-   Care managers
-   Transitional-care nurses
-   Pharmacists
-   Contact-center staff who work the escalation queue

## Target opportunity / wedge

The strongest recommended wedge in the BRD is:

> **Transitions-of-care navigator for HRRP conditions --- especially
> heart failure, COPD, AMI and pneumonia --- for mid-size/community
> hospitals and affiliated primary-care groups, particularly non-Epic or
> Epic Community Connect environments.**

The BRD explicitly concludes that the market gap is **segment and
execution**, not the invention of a new chatbot category.

------------------------------------------------------------------------

# 6. Core Solution Architecture

## 6.1 Patient Context

The patient context layer assembles information from:

-   FHIR R4 `Patient`
-   `Condition`
-   `MedicationRequest`
-   `CarePlan`
-   `Appointment`
-   `Observation`
-   `DocumentReference`
-   pharmacy-fill data

The context passed to the conversation should be patient-specific and
relevant to the current interaction.

## 6.2 Knowledge Grounding

Trusted sources identified in the BRD include:

-   MedlinePlus Connect
-   openFDA
-   DailyMed
-   RxNorm

Drug and condition answers should be grounded in authoritative content
rather than model memory alone.

## 6.3 Proactive Outreach Engine

Key event-driven workflows include:

-   discharge outreach within the required post-discharge window;
-   24--48 hour check;
-   day 7/14 follow-up confirmation;
-   refill-gap detection;
-   adherence check-ins;
-   pre-visit preparation;
-   reminder before appointments;
-   episode closeout.

## 6.4 Deterministic Clinical Guardrails

The rule engine runs before/around the LLM workflow and can override
model output.

It checks for:

-   emergency red flags,
-   medication-dose-change requests,
-   diagnosis requests,
-   lab interpretation,
-   self-harm language,
-   other out-of-scope content.

Rules are intended to be versioned and signed off by clinical
governance.

## 6.5 Human Escalation

Escalations can be routed to appropriate internal queues such as:

-   nurse/care team,
-   pharmacist,
-   scheduling workflow,
-   social-work/support workflow.

The escalation contains structured context so the human does not have to
reconstruct the situation from scratch.

## 6.6 Governance and Evidence

The BRD calls for:

-   audit logging,
-   AI disclosure,
-   bias-review documentation,
-   offline red-team testing,
-   acuity-accuracy evaluation,
-   readability checks,
-   outcome dashboards.

------------------------------------------------------------------------

# 7. End-to-End Patient Workflow

``` text
Hospital Discharge
       ↓
Patient Enrollment
       ↓
AI Disclosure + Human Contact Option
       ↓
Load Patient Context
       ↓
24–48 Hour Check-in
       ↓
Medication / Symptom / Follow-up Questions
       ↓
Ground Answer in Patient Record + Trusted Knowledge
       ↓
Safety / Scope Check
       ↓
 ┌───────────────┬──────────────────┐
 │ Safe          │ Guardrail Hit    │
 ↓               ↓
AI Response      Fixed Safe Response
 │               ↓
 │           Escalation
 │               ↓
 │          Care-Team Queue
 │               ↓
 │          Human Intervention
 │               ↓
 └───────────────┘
       ↓
Follow-up Confirmation
       ↓
Refill / Adherence Checks
       ↓
30-Day Episode Closeout
       ↓
Population-Level Outcomes
```

------------------------------------------------------------------------

# 8. Emergency Safety Flow

Emergency examples in the BRD include:

-   chest pain,
-   difficulty breathing,
-   FAST stroke signs,
-   suicidal ideation.

The flow is:

``` text
Red Flag Detected
       ↓
Override Normal AI Response
       ↓
Fixed Approved Emergency Instruction
       ↓
911 / 988 or appropriate emergency instruction
       ↓
Care-Team Alert
       ↓
Clinical Review / Action
       ↓
Documentation / Audit
```

The BRD does not specify detailed clinical treatment protocols after the
alert; therefore implementation should not invent such protocols.

------------------------------------------------------------------------

# 9. Medication Safety Flow

Example from the BRD:

> Patient asks whether they can stop a medication because they are
> dizzy.

The Navigator should **not** tell the patient to stop the medication.

Instead:

``` text
Dose-change request detected
       ↓
No medication-change advice
       ↓
Same-day human escalation
       ↓
Patient's words + medication context
       ↓
Nurse / appropriate care-team queue
       ↓
Human contact
       ↓
Document action
```

------------------------------------------------------------------------

# 10. Roles

## Patient / Caregiver

-   Interact with Navigator.
-   Ask care questions.
-   Receive reminders and education.
-   Respond to proactive check-ins.
-   Confirm medications/follow-up information.
-   Request human assistance.
-   Provide patient-reported information.

## Care Manager

-   Manage care-navigation episodes.
-   Review escalations.
-   Coordinate patient follow-up.
-   Support care-management workflows.
-   Review outcomes.

## Transitional-Care Nurse

-   Work post-discharge escalation queue.
-   Review conversation and patient context.
-   Contact patient.
-   Document intervention.
-   Support TCM/APCM-related clinical contact.

## Pharmacist

-   Handle medication-related escalations.
-   Review medication context.
-   Support medication/adherence issues.
-   Contact the patient where appropriate.
-   Document action.

## Social Worker

-   Handle support/social-related escalations.
-   Contact patients when appropriate.
-   Provide appropriate support/resources.
-   Document action.

The BRD identifies social work as an escalation destination but does not
define a detailed social-worker workflow.

## Population Health Manager

-   Monitor enrollment.
-   Monitor response rates.
-   Monitor escalation types.
-   Monitor TCM contact compliance.
-   Monitor follow-up completion.
-   Monitor readmissions and outcomes.
-   Compare enrolled patients/cohorts.

## Clinical Governance User

-   Review and approve safety rules.
-   Govern clinical guardrails.
-   Review evaluation/red-team results.
-   Review AI safety evidence.
-   Maintain governance oversight.

## System Administrator

-   Manage system configuration.
-   Manage users/roles and operational configuration.
-   Configure integrations and organization settings.

This role is an implementation/administrative role derived from the
system requirements; the BRD does not provide a detailed admin workflow.

## Important workflow-only destinations

**Scheduling is an internal workflow/destination, not necessarily a
separate application login role.**

The BRD mentions booking/scheduling where integrated and routing to a
scheduler, but this should not automatically be modeled as a separate
`SCHEDULER` application role.

------------------------------------------------------------------------

# 11. Functional Capability Areas

The backlog/specification is organized around these functional areas:

1.  Patient Enrollment
2.  Patient Data Retrieval
3.  Patient Context Assembly
4.  Conversational AI
5.  Knowledge Grounding
6.  Medication Assistance
7.  Medication Adherence
8.  Patient Understanding / Education
9.  Follow-up Management
10. Proactive Outreach
11. Red-Flag Detection
12. Clinical Guardrails
13. Emergency Response
14. Human Escalation
15. Care-Team Console
16. TCM Support
17. APCM Support
18. RPM Support
19. Population Dashboard
20. Audit Logging
21. AI Disclosure
22. Administration / Configuration

------------------------------------------------------------------------

# 12. Data and Integration Requirements

## Clinical data

FHIR R4 is the primary clinical exchange standard.

Relevant resources:

  Resource            Purpose
  ------------------- -----------------------------------
  Patient             Patient identity/context
  Condition           Active/relevant conditions
  MedicationRequest   Prescribed medications
  CarePlan            Care plan
  Appointment         Upcoming/follow-up appointments
  Observation         Relevant vitals/observations
  DocumentReference   Discharge summaries and documents

## Pharmacy data

Pharmacy-fill data is important because:

**prescribed medication ≠ medication actually filled.**

It supports refill-gap and adherence logic.

## Patient-provided information

The patient may provide information through conversation, such as:

-   symptoms,
-   medication pickup,
-   barriers,
-   reported measurements,
-   questions,
-   concerns.

Patient-reported information must not silently be represented as
authoritative EHR data.

------------------------------------------------------------------------

# 13. Communication Channels

The BRD identifies:

-   SMS
-   Web chat
-   Patient portal
-   Voice in production

The deployment should operate under the healthcare organization's own
brand.

------------------------------------------------------------------------

# 14. Compliance and Regulatory Scope

The BRD identifies several important considerations.

## AB 3030

California requirements for generative-AI clinical communications
include AI disclosure and instructions for reaching a human unless the
applicable licensed-provider review exception applies.

## Texas TRAIGA

Texas requires disclosure of AI use in applicable healthcare
services/treatment.

## Section 1557

Covered entities need to identify and mitigate discrimination risks
associated with patient-care decision-support tools.

## FDA CDS scope

Patient-facing software that informs clinical decisions can fall within
device/CDS regulatory considerations.

The Navigator should remain on the:

**education / navigation / escalation**

side rather than diagnostic or treatment decision-making.

## FTC / consumer health data

The BRD also highlights scrutiny around consumer health data and AI
chatbot behavior, particularly where consumer channels may not fit a
traditional HIPAA environment.

------------------------------------------------------------------------

# 15. Non-Functional Requirements

## Safety

-   100% scripted emergency escalation recall.
-   Zero missed live emergencies on audit.

## Record grounding

-   Medication and appointment facts should match the source record.
-   Target: **100% grounding accuracy** for these facts.

## Human-in-the-loop

Clinical escalation must be reviewable by appropriate human staff.

## Security

The BRD identifies **SOC 2 Type II** and **HITRUST** as credentials
expected by healthcare buyers.

## Privacy

Healthcare and conversation data must be protected appropriately.

## Availability

The product vision expects between-visit support at any hour.

## Performance

The BRD does not define a specific numeric latency target.

## Scalability

Demo data targets 100--500 synthetic patients; production scale is not
numerically defined in the BRD.

## Explainability / Traceability

Conversations, escalation decisions and relevant actions should be
auditable.

## Readability

Target median response readability:

**Flesch-Kincaid grade 6--8.**

## Usability

The patient experience should be simple, mobile-friendly and provide a
clear human-contact option.

## Clinical Governance

Safety rules should be:

-   versioned,
-   reviewed,
-   approved/signed off,
-   evaluated.

## Interoperability

FHIR R4 is the core interoperability approach.

## Auditability

Every conversation turn and relevant care-team action should be
traceable.

## Patient trust

Target:

-   helpfulness ≥80%;
-   opt-out \<10%.

## Clinician workload

Target:

**No net increase in clinician message minutes per 1,000 enrolled
patients.**

------------------------------------------------------------------------

# 16. Success Metrics

  -----------------------------------------------------------------------
  Metric                              Target
  ----------------------------------- -----------------------------------
  Red-flag escalation recall          100% scripted scenarios; zero
                                      missed live emergencies on audit

  Record grounding                    100% medication/appointment facts
                                      match source

  TCM contact                         ≥90% eligible discharges within
                                      required window

  7/14-day follow-up                  +15--20 percentage points vs
                                      baseline; hypothesis

  30-day readmission                  10--15% relative reduction vs
                                      matched cohort; hypothesis

  Medication adherence                +5--10 percentage points for PDC
                                      ≥80%; hypothesis

  Patient questions resolved without  ≥60% while escalation recall
  staff                               remains 100%

  Reading level                       Median grade 6--8

  Clinician workload                  No net increase in message minutes
                                      per 1,000 enrolled

  Patient trust/helpfulness           ≥80%

  Opt-out                             \<10%
  -----------------------------------------------------------------------

Outcome reductions are explicitly treated as hypotheses to validate
rather than guaranteed product results.

------------------------------------------------------------------------

# 17. Business Value

The Navigator is intended to create value in four areas:

### 1. Better patient support

Patients receive continuous support between appointments.

### 2. Better care transitions

Post-discharge activities become structured and trackable.

### 3. Greater care-team capacity

Routine questions can be handled by the Navigator while higher-risk
issues are routed to humans.

### 4. Documented care-management work

The system helps turn eligible care-management activities into completed
and documented workflows.

The BRD emphasizes that AI contact alone should not be assumed to
satisfy TCM interactive-contact requirements.

------------------------------------------------------------------------

# 18. TCM / APCM / RPM

## TCM --- Transitional Care Management

Focus:

**After hospital discharge.**

Key workflow:

``` text
Discharge
 ↓
Post-discharge contact
 ↓
Medication / symptom / follow-up checks
 ↓
Human clinical contact
 ↓
Follow-up visit
 ↓
Documentation
```

The BRD identifies CPT 99495/99496 and the associated contact/follow-up
requirements.

## APCM --- Advanced Primary Care Management

Focus:

**Ongoing team-based primary care.**

The Navigator can support:

-   continuous access,
-   digital communication,
-   follow-up,
-   care-team workflows,
-   documentation.

## RPM --- Remote Physiologic Monitoring

Focus:

**Monitoring patient physiologic data from home.**

Examples include weight and other measurements.

The Navigator can support patient engagement and routing, but
monitoring/billing requirements remain clinical/organizational
responsibilities.

------------------------------------------------------------------------

# 19. Competitive Landscape

The BRD identifies several competitor categories.

## EHR-native

-   Epic / MyChart / Emmie

## AI-native agents

-   Hippocratic AI
-   K Health

## Care-navigation platforms

-   Memora Health / Commure
-   Get Well / SAI Group
-   Amwell Automated Care Programs
-   care.coach

## Patient communication/access

-   Artera
-   Luma Health
-   Notable
-   Cedar

## Digital front door / virtual triage

-   Clearstep
-   Fabric
-   Infermedica
-   Ada Health

## Payer engagement

-   HealthEdge Wellframe
-   Lirio
-   Laguna Health

## Chronic-condition programs

-   Welldoc
-   Omada Health
-   Lightbeam

The BRD also recognizes general-purpose consumer AI and in-house
provider-built solutions as competitive alternatives.

------------------------------------------------------------------------

# 20. Gap Analysis

The BRD explicitly says the market is crowded.

## Claims that are NOT real differentiators

These are already available in the market:

-   conversational patient AI,
-   patient-record personalization,
-   safety guardrails,
-   basic patient navigation.

Therefore:

> **Do not position the product simply as "an AI chatbot for
> patients."**

## Real or partially real opportunities

1.  Billable/auditable care-management workflow.
2.  Deterministic safety evidence.
3.  Record-grounded navigation for non-Epic organizations.
4.  Independent outcome evidence.
5.  Health-literacy-adapted and multilingual explanations.
6.  State-configurable AI disclosure.
7.  Payer navigation using pharmacy-fill/adherence signals.

------------------------------------------------------------------------

# 21. Recommended Differentiation

The BRD's strongest differentiation is:

### Wedge

**Transitions-of-care navigator for HRRP conditions**, especially:

-   heart failure,
-   COPD,
-   AMI,
-   pneumonia.

### Target

-   mid-size/community hospitals,
-   non-Epic organizations,
-   Epic Community Connect organizations,
-   affiliated primary-care groups,
-   value-based organizations,
-   selected payer use cases.

### Positioning

Build the organization's **own governed navigator**, rather than selling
an opaque generic chatbot.

### Evidence package

Potential evidence/compliance assets include:

-   AB 3030 / TRAIGA disclosure templates,
-   Section 1557 bias-review worksheet,
-   FDA CDS/General Wellness scope memo,
-   red-team acuity test suite,
-   pre-registered readmission evaluation design.

------------------------------------------------------------------------

# 22. Risks and Open Questions

  -------------------------------------------------------------------------------------
  Risk / Question             Impact                  BRD Direction
  --------------------------- ----------------------- ---------------------------------
  Epic expands Emmie          Could reduce            Track Epic releases and interview
                              third-party need in     Community Connect affiliates
                              Epic accounts           

  Missed emergency escalation Patient harm,           Deterministic escalation + 100%
                              legal/reputational      red-team gate + clinician review
                              exposure                

  Readmission benefit smaller ROI case weakens        Matched-cohort evaluation; use
  than expected                                       TCM/follow-up as leading
                                                      indicators

  AI-only contact doesn't     Billing audit risk      Design for staff contact; obtain
  satisfy TCM                                         coding/compliance review

  State-law changes           Disclosure design may   Configurable state rules + legal
                              need changes            review

  FDA scope changes           Regulatory burden       Formal intended-use statement; no
                                                      diagnostic outputs

  EHR                         Deployment complexity   Plan for FHIR/EHR integration and
  integration/certification                           certification

  Security credentials        Buyer acceptance        SOC 2 Type II / HITRUST readiness

  Clinical content licensing  Limits symptom/triage   Stay within
                              scope                   navigation/education/escalation

  Clinical liability          Governance burden       Clinician oversight and incident
                                                      response

  Competition                 Crowded market          Focus on segment + execution
  -------------------------------------------------------------------------------------

------------------------------------------------------------------------

# 23. Demo / MVP Data

The BRD recommends **synthetic data**, not real PHI.

## Primary source

**Synthea synthetic patient data.**

It provides:

-   FHIR R4 bundles,
-   CSV,
-   clinical notes,
-   synthetic longitudinal records.

## FHIR server

The BRD suggests using a FHIR server such as **HAPI FHIR** to simulate
EHR API access.

## Demo population

Target:

-   100--500 synthetic patients,
-   8--10 curated showcase patients.

Example showcase profiles:

-   heart-failure post-discharge,
-   COPD,
-   type 2 diabetes,
-   anticoagulated atrial fibrillation,
-   polypharmacy older adult,
-   Spanish-preferring patient.

## Demo information

Include:

-   discharge information,
-   medication reconciliation,
-   care plans,
-   follow-up appointments,
-   pharmacy fills,
-   refill gaps,
-   daily weights/vitals,
-   clinical notes.

The BRD suggests realistic refill-gap scenarios and synthetic
post-discharge workflows.

------------------------------------------------------------------------

# 24. Example Patient Journey

### Day 0 --- Discharge

Hospital enrolls patient.

Navigator loads:

-   discharge summary,
-   medication reconciliation,
-   care plan,
-   follow-up orders.

Patient receives:

-   introduction,
-   AI disclosure,
-   human-contact option.

### Day 1--2

Navigator asks:

-   Were medications picked up?
-   Does the patient understand new medications?
-   Are there symptoms mentioned in discharge instructions?

### Patient question

Patient asks:

> "Why am I taking two blood-pressure medicines?"

Navigator:

-   retrieves patient's medications,
-   uses trusted knowledge,
-   explains in plain language,
-   checks understanding.

### Safety event

Patient says:

> "I have chest pain."

Deterministic rule:

``` text
Chest pain
   ↓
Stop normal AI response
   ↓
Fixed emergency instruction
   ↓
Emergency guidance
   ↓
Care-team alert
   ↓
Audit
```

### Non-emergency clinical issue

Patient says:

> "Can I stop my carvedilol? I'm dizzy."

Navigator:

``` text
Dose-change request
   ↓
No stop/change advice
   ↓
Same-day nurse escalation
   ↓
Patient words + medication context
   ↓
Human intervention
```

### Day 7/14

Navigator checks follow-up status.

### During the next 30 days

-   appointment reminder,
-   refill-gap detection,
-   adherence check,
-   patient understanding/satisfaction closeout.

### Population level

Population Health Manager reviews:

-   enrollment,
-   response,
-   escalation,
-   TCM compliance,
-   follow-up completion,
-   readmissions.

------------------------------------------------------------------------

# 25. Governance Model

The product should use:

``` text
Clinical Governance
       ↓
Safety Rules
       ↓
Version + Approval
       ↓
Deployment
       ↓
Red-Team / Evaluation
       ↓
Results Review
       ↓
Rule Updates
```

The LLM should not be the final authority for safety decisions.

**Rule engine decides safety behavior.\
LLM assists with language.**

------------------------------------------------------------------------

# 26. Audit and Evidence

The system should preserve evidence for:

-   patient interactions,
-   AI disclosure,
-   escalation triggers,
-   emergency instructions,
-   human escalation,
-   care-team response,
-   relevant care-management events,
-   rule versions,
-   governance approval,
-   evaluation results.

This supports safety review, governance, operational reporting and
compliance.

------------------------------------------------------------------------

# 27. Suggested MVP Capability Boundary

The core MVP should demonstrate the complete closed-loop journey:

``` text
Patient Enrollment
       ↓
FHIR Patient Context
       ↓
AI Conversation
       ↓
Trusted Knowledge Grounding
       ↓
Medication / Follow-up Support
       ↓
Deterministic Safety
       ↓
Human Escalation
       ↓
Care-Team Console
       ↓
Care-Team Action
       ↓
Documentation
       ↓
Outcome Dashboard
```

The MVP should prove the **workflow**, not merely demonstrate a chatbot.

------------------------------------------------------------------------

# 28. Important Design Principles

1.  **Record-grounded first.**
2.  **Deterministic safety over LLM judgment.**
3.  **Human in the loop.**
4.  **No diagnosis or prescribing.**
5.  **Every important interaction is auditable.**
6.  **Plain language by default.**
7.  **Proactive, event-driven outreach.**
8.  **Patient-specific rather than generic responses.**
9.  **Support care-team capacity rather than add inbox work.**
10. **Measure clinical/operational outcomes.**
11. **Keep state-specific disclosures configurable.**
12. **Design for non-Epic environments as a key wedge.**
13. **Use synthetic data for development/demo.**
14. **Treat TCM/APCM/RPM as workflow/business contexts, not merely
    chatbot features.**

------------------------------------------------------------------------

# 29. Glossary

  -----------------------------------------------------------------------
  Term                                Meaning
  ----------------------------------- -----------------------------------
  **AI Navigator**                    Patient-facing between-visit
                                      care-navigation assistant

  **LLM**                             Large Language Model

  **FHIR R4**                         Healthcare data exchange/API
                                      standard

  **TCM**                             Transitional Care Management

  **APCM**                            Advanced Primary Care Management

  **RPM**                             Remote Physiologic Monitoring

  **HRRP**                            Hospital Readmissions Reduction
                                      Program

  **PDC**                             Proportion of Days Covered

  **PQA**                             Pharmacy Quality Alliance

  **ACCESS**                          CMS Innovation Center
                                      outcome-aligned chronic-care model

  **Deterministic Guardrail**         Fixed rule that can override LLM
                                      output

  **Escalation**                      Transfer from AI to human care team
                                      or emergency instruction

  **Health Literacy**                 Ability to obtain, understand and
                                      use health information

  **AB 3030**                         California AI
                                      disclosure/human-contact
                                      requirement described in the BRD

  **TRAIGA**                          Texas AI regulation referenced for
                                      healthcare disclosure

  **Section 1557**                    ACA nondiscrimination requirements
                                      relevant to decision-support tools

  **SOC 2 / HITRUST**                 Security/privacy assurance
                                      frameworks expected by healthcare
                                      buyers

  **Flesch-Kincaid**                  Readability measure used for
                                      response reading level
  -----------------------------------------------------------------------

------------------------------------------------------------------------

# 30. Final Product Definition

The Patient AI Health Navigator is best understood as:

> **A governed, record-grounded, between-visit care-navigation layer
> that helps healthcare organizations support patients after discharge
> and between appointments, automates appropriate
> education/reminders/check-ins, detects safety and scope issues using
> deterministic rules, routes significant issues to human care teams,
> and produces auditable care-management and outcome evidence.**

The strongest business proposition is **not "AI chatbot."**

It is:

> **Personalized care navigation + deterministic safety + human
> escalation + documented care-management workflow + measurable
> outcomes.**
