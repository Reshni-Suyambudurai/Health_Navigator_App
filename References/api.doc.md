Yes. Based on the DB structure we've already established for your **Patient AI Health Navigator**, you currently have these clinical tables in PostgreSQL:

```text
patients
fhir_resources
conditions
medications
care_plans
encounters
observations
appointments
```

You dropped `allergy_intolerances` and `clinical_documents` for now.

But for the **actual application**, APIs cannot stop at CRUD for those 8 tables. You also need APIs for **patient enrollment, context, conversation, escalation, care-team actions, and outreach**.

## 1. Recommended API structure

I would divide your FastAPI APIs into these modules:

```text
/api
│
├── auth
├── patients
├── patient-context
├── conditions
├── medications
├── care-plans
├── encounters
├── observations
├── appointments
├── conversations
├── escalations
├── care-team
├── outreach
└── dashboard
```

---

# 2. Patient APIs

These are the basic APIs around your `patients` table.

### Get all patients

```http
GET /api/patients
```

For Care-Team Portal.

Example:

```json
[
  {
    "id": "uuid",
    "fhir_patient_id": "2310",
    "name": "Agnus Brown",
    "date_of_birth": "1980-01-01",
    "gender": "male"
  }
]
```

### Get one patient

```http
GET /api/patients/{patient_id}
```

### Get patient by FHIR ID

```http
GET /api/patients/fhir/{fhir_patient_id}
```

Example:

```http
GET /api/patients/fhir/2310
```

### Create patient

```http
POST /api/patients
```

### Update patient

```http
PUT /api/patients/{patient_id}
```

---

# 3. Patient Context API ⭐

This is one of the **most important APIs in your application**.

Don't make Angular fetch 50 Conditions + 20 medications + 100 observations and build the patient context itself.

Your backend should assemble it.

### Get complete patient context

```http
GET /api/patients/{patient_id}/context
```

Response could be:

```json
{
  "patient": {
    "id": "2310",
    "name": "Agnus Brown",
    "age": 67
  },

  "conditions": [
    {
      "name": "Heart Failure",
      "status": "active"
    }
  ],

  "medications": [
    {
      "name": "Apixaban",
      "status": "active"
    }
  ],

  "care_plans": [],
  "recent_encounters": [],
  "recent_observations": [],
  "upcoming_appointments": [],

  "recent_discharge": {},
  
  "risk_flags": []
}
```

This is what your **AI conversation layer** should consume.

The BRD specifically says the Patient Context layer assembles a per-patient profile from the patient's FHIR data and passes **only that profile** to the conversation layer. UC-HC-03_Patient-AI-Health-Navi…

### Refresh context

```http
POST /api/patients/{patient_id}/context/refresh
```

Useful when new FHIR data arrives.

### Get context summary

```http
GET /api/patients/{patient_id}/context/summary
```

For Care-Team UI.

---

# 4. Conditions APIs

Table:

```text
conditions
```

### Get patient conditions

```http
GET /api/patients/{patient_id}/conditions
```

### Get active conditions

```http
GET /api/patients/{patient_id}/conditions/active
```

### Get one condition

```http
GET /api/conditions/{condition_id}
```

You probably don't need patient-side `POST/PUT` for these initially because **HAPI FHIR is your clinical source of truth**.

---

# 5. Medication APIs ⭐

Table:

```text
medications
```

### Get patient medications

```http
GET /api/patients/{patient_id}/medications
```

### Get active medications

```http
GET /api/patients/{patient_id}/medications/active
```

### Get medication

```http
GET /api/medications/{medication_id}
```

### Medication history

```http
GET /api/patients/{patient_id}/medications/history
```

This becomes important for questions such as:

> "I started a new medicine yesterday."

The backend needs to know **which medication was recently started**.

---

# 6. Care Plan APIs

Table:

```text
care_plans
```

### Get patient care plans

```http
GET /api/patients/{patient_id}/care-plans
```

### Get active care plans

```http
GET /api/patients/{patient_id}/care-plans/active
```

### Get specific care plan

```http
GET /api/care-plans/{care_plan_id}
```

---

# 7. Encounter APIs

Table:

```text
encounters
```

### Get encounters

```http
GET /api/patients/{patient_id}/encounters
```

### Get recent encounters

```http
GET /api/patients/{patient_id}/encounters/recent
```

### Get latest hospitalization

```http
GET /api/patients/{patient_id}/encounters/latest-hospitalization
```

This is useful for the post-discharge workflow.

---

# 8. Observation APIs

Table:

```text
observations
```

### Get observations

```http
GET /api/patients/{patient_id}/observations
```

### Get recent observations

```http
GET /api/patients/{patient_id}/observations/recent
```

### Get observations by code

```http
GET /api/patients/{patient_id}/observations/{code}
```

For example:

```text
Blood pressure
Weight
Glucose
HbA1c
Respiratory rate
```

### Get latest value

```http
GET /api/patients/{patient_id}/observations/{code}/latest
```

---

# 9. Appointment APIs

Table:

```text
appointments
```

These are important because your BRD has **7/14-day follow-up confirmation**.

### Get appointments

```http
GET /api/patients/{patient_id}/appointments
```

### Get upcoming appointments

```http
GET /api/patients/{patient_id}/appointments/upcoming
```

### Get next appointment

```http
GET /api/patients/{patient_id}/appointments/next
```

### Create appointment

```http
POST /api/patients/{patient_id}/appointments
```

### Update appointment

```http
PUT /api/appointments/{appointment_id}
```

### Cancel appointment

```http
DELETE /api/appointments/{appointment_id}
```

If scheduling becomes an external integration later, these APIs can call the scheduling system instead of directly modifying your DB.

---

# 10. FHIR Resource APIs

Table:

```text
fhir_resources
```

I would **not expose unrestricted raw FHIR JSON to the patient frontend**.

But the backend/admin side may need:

### Get FHIR resources

```http
GET /api/fhir/patients/{patient_id}/resources
```

### Get specific resource type

```http
GET /api/fhir/patients/{patient_id}/resources/{resource_type}
```

Example:

```http
GET /api/fhir/patients/2310/resources/MedicationRequest
```

### Get specific FHIR resource

```http
GET /api/fhir/resources/{resource_type}/{resource_id}
```

Example:

```http
GET /api/fhir/resources/Patient/2310
```

This is mainly for backend/integration/debugging.

---
