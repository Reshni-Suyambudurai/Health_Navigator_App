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

## Frontend Setup

The frontend is an Angular 22 standalone application located in `Frontend/`.

### 1. Prerequisites

- Node.js and npm
- Backend API running at `http://localhost:8000`

### 2. Install frontend dependencies

```powershell
cd Frontend
npm install
```

### 3. Run the development server

```powershell
npm start
```

Open `http://localhost:4200` in a browser. The development environment uses the API base URL:

```text
http://localhost:8000/api/v1
```

This is configured in `Frontend/src/environments/environment.development.ts`.

### 4. Build and test

```powershell
npm run build
npm test
```

Use `npm run build -- --configuration development` when validating a development build.

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

Seeded users and login password:

| Email | Password | Role |
|---|---|---|
| `john.doe@example.com` | `Test@1234` | `PATIENT` |
| `sarah.johnson@cityhospital.com` | `Test@1234` | `CARE_MANAGER` |
| `michael.chen@communityclinic.com` | `Test@1234` | `TRANSITIONAL_CARE_NURSE` |
| `emma.williams@midwesthealthcare.com` | `Test@1234` | `SYSTEM_ADMIN` |
| `demo.admin@patientai.local` | `Test@1234` | `SYSTEM_ADMIN` |
| `care.manager@patientai.local` | `Test@1234` | `CARE_MANAGER` |
| `aguns790.2310@patientai.local` | `Test@1234` | `PATIENT` |
| `bettyann83.3942@patientai.local` | `Test@1234` | `PATIENT` |
| `carl856.5991@patientai.local` | `Test@1234` | `PATIENT` |

Notes:

- Yes, all users above are intended to use the same password: `Test@1234`.
- If your DB was seeded before bcrypt hash corrections, run migrations/refresh seed data or reset these users' `password_hash` values.

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

## Frontend Folder Structure

```text
Frontend/
├── angular.json                         # Angular workspace configuration
├── package.json                          # npm scripts and dependencies
├── public/                               # Static public assets
└── src/
	├── environments/                     # API and build environment settings
	├── main.ts                            # Angular bootstrap entry point
	├── styles.scss                        # Shared theme, dark mode, tables, and UI styles
	└── app/
		├── api/
		│   ├── navigator/                # Navigator API clients
		│   ├── patientfhir/              # Patient FHIR API clients
		│   └── tokenstore.ts             # Session and local-storage access
		├── components/
		│   └── roles/                    # Role-specific screens and components
		├── shared/
		│   ├── layout/                   # Shell, sidebar, navbar, and shared layout
		│   ├── types/                    # Shared API and domain interfaces
		│   ├── ui/                       # Toasts and reusable UI components
		│   └── utils/                    # Theme and routing utilities
		├── app.config.ts                 # Application providers
		└── app.ts                         # Root component and application routes
```

Frontend conventions:

- Keep API calls in `src/app/api/` and related interfaces in `src/app/shared/types/`.
- Place role-specific components under `src/app/components/roles/<role-name>/`.
- Reuse `src/styles.scss`, the shared toast service, and `tokenstore.ts`.
- Add routes in `src/app/app.ts`.
