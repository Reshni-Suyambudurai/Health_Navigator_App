"""
FastAPI main application entry point for Patient AI Health Navigator
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.utils.logger import setup_logging
from app.database.connection import check_database_connection, check_monster_database_connection
from app.api.routes.navigator import user_routes
from app.api.routes.navigator import patient_profile_routes
from app.api.routes.navigator import patient_consent_record_routes
from app.api.routes.navigator import patient_enrollment_routes
from app.api.routes.navigator import patient_intake_routes
from app.api.routes.navigator import patient_onboarding_routes
from app.api.routes.navigator import conversation_routes
from app.api.routes.patientFHIR import patient_fhir_routes
from app.core.exception_handlers import register_exception_handlers  # Import exception handlers
import logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle handler for startup/shutdown logic."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")

    # Check local application DB connection
    if check_database_connection():
        logger.info("Database connection verified")
    else:
        logger.error("Database connection failed - application may not function properly")

    # Check Monster DB connection (read-only patient FHIR source)
    if check_monster_database_connection():
        logger.info("Monster database connection verified")
    else:
        logger.warning("Monster database connection unavailable - PatientFHIR endpoints may not function")

    yield

    logger.info(f"Shutting down {settings.APP_NAME}")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Patient AI Health Navigator - Backend API for between-visit patient support",
    debug=settings.DEBUG,
    lifespan=lifespan,
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Register global exception handlers
register_exception_handlers(app)

# Enable CORS for frontend applications
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

# Include API routers
app.include_router(user_routes.router, prefix="/api/v1")
app.include_router(patient_profile_routes.router, prefix="/api/v1")
app.include_router(patient_consent_record_routes.router, prefix="/api/v1")
app.include_router(patient_enrollment_routes.router, prefix="/api/v1")
app.include_router(patient_intake_routes.router, prefix="/api/v1")
app.include_router(patient_onboarding_routes.router, prefix="/api/v1")
app.include_router(conversation_routes.router, prefix="/api/v1")
app.include_router(patient_fhir_routes.router, prefix="/api/v1")


@app.get("/", tags=["Health"])
async def root():
    """
    Root endpoint - basic application information
    """
    return {
        "application": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint
    """
    db_status = check_database_connection()
    
    if db_status:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "healthy",
                "database": "connected",
                "version": settings.APP_VERSION
            }
        )
    else:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "database": "disconnected",
                "version": settings.APP_VERSION
            }
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
