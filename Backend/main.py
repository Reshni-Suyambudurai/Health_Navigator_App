"""
FastAPI main application entry point for Patient AI Health Navigator
"""

from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from app.config import settings
from app.utils.logger import setup_logging
from app.database.connection import check_database_connection
from app.api.routes import user_routes  # Import user routes
from app.core.exception_handlers import register_exception_handlers  # Import exception handlers
import logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Patient AI Health Navigator - Backend API for between-visit patient support",
    debug=settings.DEBUG
)

# Register global exception handlers
register_exception_handlers(app)

# Include API routers
app.include_router(user_routes.router, prefix="/api/v1")

@app.on_event("startup")
async def startup_event():
    """
    Application startup event
    """
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    
    # Check database connection
    if check_database_connection():
        logger.info("Database connection verified")
    else:
        logger.error("Database connection failed - application may not function properly")


@app.on_event("shutdown")
async def shutdown_event():
    """
    Application shutdown event
    """
    logger.info(f"Shutting down {settings.APP_NAME}")


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
