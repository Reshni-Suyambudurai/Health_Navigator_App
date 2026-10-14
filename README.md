# Patient AI Health Navigator - Backend

Backend API for the Patient AI Health Navigator system - a healthcare care-navigation platform providing between-visit patient support.

## Tech Stack

- **FastAPI 0.115.0** - Modern web framework for building APIs
- **SQLAlchemy 2.0.35** - SQL toolkit and ORM
- **PostgreSQL** - Relational database
- **Alembic 1.13.2** - Database migration tool
- **Pydantic** - Data validation
- **Uvicorn** - ASGI server

## Project Structure

```
backend/
├── alembic/                         # Alembic migration environment
│   ├── versions/                    # Migration version files
│   │   ├── ba266a56e651_initial_schema_with_auth_tables.py
│   │   └── 880a89792d14_insert_mock_data.py
│   ├── env.py                       # Migration environment config
│   ├── README                       # Alembic instructions
│   └── script.py.mako              # Migration template
├── app/
│   ├── __init__.py
│   ├── config.py                    # Configuration management
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       └── user_routes.py       # User/auth endpoints
│   ├── core/
│   │   ├── __init__.py
│   │   ├── exceptions.py            # Custom exception classes
│   │   ├── exception_handlers.py   # Global exception handlers
│   │   └── response_models.py      # Standardized response formats
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection.py            # Database connection and session
│   │   ├── models/                  # SQLAlchemy models
│   │   │   ├── __init__.py
│   │   │   ├── organization.py
│   │   │   ├── role.py
│   │   │   ├── user.py
│   │   │   ├── patient_profile.py
│   │   │   ├── staff_profile.py
│   │   │   └── audit_log.py
│   │   └── repositories/            # Data access layer
│   │       ├── __init__.py
│   │       └── user_repository.py
│   ├── services/                    # Business logic layer
│   │   ├── __init__.py
│   │   └── user_service.py
│   └── utils/
│       ├── __init__.py
│       └── logger.py                # Logging configuration
├── tests/
│   └── __init__.py
├── .claude.md                       # Architecture instructions for AI
├── .env.example                     # Environment variables template
├── .gitignore
├── alembic.ini                      # Alembic configuration file
├── main.py                          # Application entry point
├── requirements.txt
└── README.md
```

## Setup Instructions

### 1. Prerequisites

- **Python 3.8+** installed
- **PostgreSQL** installed and running
- **Git** for version control

### 2. Clone Repository

```powershell
git clone <repository-url>
cd Patient_Health_Analyzer_PoC/backend
```

### 3. Create Virtual Environment

```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment (PowerShell)
.\venv\Scripts\Activate.ps1

# Or for Command Prompt
.\venv\Scripts\activate.bat
```

### 4. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 5. Configure Environment Variables

```powershell
# Copy the example environment file
copy .env.example .env

# Edit .env with your actual database credentials
notepad .env
```

**Update the following in your `.env` file:**
```env
DATABASE_URL=postgresql://your_username:your_password@localhost:5432/your_database_name
APP_NAME="Patient AI Health Navigator"
APP_VERSION="0.1.0"
DEBUG=True
LOG_LEVEL=INFO
HOST=localhost
PORT=8000
```

**IMPORTANT**: 
- The `DATABASE_URL` is **required** and must be set in your `.env` file
- Never commit your `.env` file to Git (it's already in `.gitignore`)
- Use `.env.example` as a template for what variables are needed

### 6. Initialize Database with Alembic

```powershell
# Run all pending migrations (creates tables + inserts mock data)
alembic upgrade head
```

**What this does:**
- ✅ Creates all database tables with proper constraints
- ✅ Sets up enum types for status fields
- ✅ Inserts mock data (4 rows per table)
- ✅ Sets up database triggers for auto-updating timestamps

### 7. Verify Setup

```powershell
# Start the application
python main.py

# Or with uvicorn directly
uvicorn main:app --reload --host localhost --port 8000
```

Access the API documentation at: http://localhost:8000/docs

## Running the Application

### Development Mode (with auto-reload)

```powershell
# Make sure virtual environment is activated
python main.py
```

Or using uvicorn directly:
```powershell
uvicorn main:app --reload --host localhost --port 8000
```

### Access the Application

- **API**: http://localhost:8000
- **API Documentation (Swagger)**: http://localhost:8000/docs
- **Alternative Documentation (ReDoc)**: http://localhost:8000/redoc

## API Endpoints

### Health Check Endpoints

- `GET /` - Root endpoint with basic application info
- `GET /health` - Health check endpoint with database status

### User/Auth Endpoints

- `POST /api/v1/users/login` - User login (email + password)
- `GET /api/v1/users/{user_id}` - Get user by ID
- `GET /api/v1/users/` - Get all users (with pagination)
- `POST /api/v1/users/` - Create new user
- `DELETE /api/v1/users/{user_id}` - Delete user
- `GET /api/v1/users/status/active` - Get all active users

## Database Schema

The application uses 6 main tables:

1. **organizations** - Healthcare organizations (4 mock rows)
2. **roles** - User roles - 9 types aligned with BRD
3. **users** - All system users (4 mock rows: 1 patient + 3 staff)
4. **patient_profiles** - Extended patient information (1 mock row)
5. **staff_profiles** - Extended staff information (3 mock rows)
6. **audit_logs** - Audit trail for system actions (4 mock rows)

### Mock Data Credentials

All mock users have the same password: **`Test@1234`**

Mock users:
- **Patient**: john.doe@example.com
- **Care Manager**: sarah.johnson@cityhospital.com
- **Transitional Care Nurse**: michael.chen@communityclinic.com
- **System Admin**: emma.williams@midwesthealthcare.com
