# Patient AI Health Navigator - Backend

## Objective

This backend provides APIs and data workflows for patient care-navigation.
It supports:

- authentication and user management
- patient navigation workflows (episodes, threads, guardrails, escalations, outreach)
- dual database usage:
	- application DB for platform data
	- Monster/FHIR source DB for patientFHIR read access

## Tech Stack

- FastAPI
- SQLAlchemy
- PostgreSQL
- Alembic
- Pydantic Settings
- Uvicorn

## Setup Instructions for Local and Monster Application DB

### 1. Prerequisites

- Python 3.12+
- PostgreSQL access (local and/or cloud)
- Virtual environment created at project root (`.venv`)

### 2. Install dependencies

```powershell
cd backend
../.venv/Scripts/python.exe -m pip install -r requirements.txt
```

### 3. Configure `DATABASE_URL` in `.env`

Create `.env` from template first:

```powershell
copy .env.example .env
```

Only one `DATABASE_URL` should be active (uncommented) at a time.

Local application DB:

```env
DATABASE_URL=postgresql://<local_user>:<local_password>@localhost:5432/patientnavigator
```

Monster/cloud application DB:

```env
DATABASE_URL=postgresql://db74082:F-y96bP%23R3_e@db74082.public.databaseasp.net:5432/db74082?sslmode=prefer
```

If using local DB, create local PostgreSQL database and user before migrations:

```sql
CREATE USER <local_user> WITH PASSWORD '<local_password>';
CREATE DATABASE patientnavigator OWNER <local_user>;
GRANT ALL PRIVILEGES ON DATABASE patientnavigator TO <local_user>;
```

### 4. Run migrations for whichever DB is enabled

```powershell
cd backend
../.venv/Scripts/python.exe -m alembic -c alembic.ini upgrade head
../.venv/Scripts/python.exe -m alembic -c alembic.ini current
```

Notes:

- migrations are idempotent where `ON CONFLICT` is used in seed scripts
- Alembic `env.py` handles URL escaping for encoded passwords (e.g. `%23`)

### 5. Run backend API

```powershell
cd backend
../.venv/Scripts/python.exe main.py
```

## Swagger

- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`
- ReDoc: `http://localhost:8000/redoc`

## Mock Data Credentials

Default mock password used in seeded users:

- `Test@1234`

Seeded workflow/demo users:

- `demo.admin@patientai.local`
- `care.manager@patientai.local`
- `aguns790.2310@patientai.local`
- `bettyann83.3942@patientai.local`
- `carl856.5991@patientai.local`

## Backend Folder Structure

```text
backend/
├── alembic/                                  # Alembic migration environment
│   ├── versions/                             # Migration version files
│   │   ├── ba266a56e651_initial_schema_with_auth_tables.py
│   │   ├── 880a89792d14_insert_mock_data.py
│   │   ├── c3f7a91d2b10_expand_schema_to_dbml_models.py
│   │   └── e8a6c1f4b2d3_seed_app_data_from_patient_fhir.py
│   ├── env.py                                # Migration environment config
│   ├── README                                # Alembic instructions
│   └── script.py.mako                        # Migration template
├── app/
│   ├── __init__.py
│   ├── config.py                             # Configuration management
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── user_routes.py                # User/auth endpoints
│   │       └── patientFHIR/                  # PatientFHIR route modules
│   ├── core/
│   │   ├── __init__.py
│   │   ├── exceptions.py                     # Custom exception classes
│   │   ├── exception_handlers.py             # Global exception handlers
│   │   └── response_models.py                # Standardized response formats
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection.py                     # Database engines and session management
│   │   ├── models/                           # SQLAlchemy models (one table per file)
│   │   │   ├── __init__.py
│   │   │   ├── organization.py
│   │   │   ├── role.py
│   │   │   ├── user.py
│   │   │   ├── patient_profile.py
│   │   │   ├── staff_profile.py
│   │   │   ├── audit_log.py
│   │   │   ├── patient_consent_record.py
│   │   │   ├── patient_enrollment.py
│   │   │   ├── care_navigation_episode.py
│   │   │   ├── conversation_thread.py
│   │   │   ├── conversation_message.py
│   │   │   ├── clinical_guardrail.py
│   │   │   ├── clinical_guardrail_rule.py
│   │   │   ├── conversation_guardrail_hit.py
│   │   │   ├── emergency_event.py
│   │   │   ├── care_team_queue.py
│   │   │   ├── queue_membership.py
│   │   │   ├── escalation.py
│   │   │   ├── escalation_assignment.py
│   │   │   ├── escalation_action.py
│   │   │   ├── outreach_campaign.py
│   │   │   ├── outreach_workflow.py
│   │   │   └── outreach_event.py
│   │   └── repositories/                     # Data access layer
│   ├── services/                             # Business logic layer
│   └── utils/                                # Utility modules (logging/helpers)
├── tests/
│   └── __init__.py
├── alembic.ini                               # Alembic configuration file
├── main.py                                   # Application entry point
├── requirements.txt
└── .env
```
