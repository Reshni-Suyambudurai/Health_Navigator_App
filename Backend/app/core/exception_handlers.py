"""
Global exception handlers for the application
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from app.core.exceptions import (
    AuthenticationException,
    AuthorizationException,
    NotFoundException,
    ValidationException,
    ConflictException,
    PatientFHIRException
)
from app.core.response_models import ErrorResponse
import logging

logger = logging.getLogger(__name__)


async def authentication_exception_handler(request: Request, exc: AuthenticationException):
    """Handle authentication exceptions (401)"""
    logger.warning(f"Authentication failed: {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content=ErrorResponse(
            status="error",
            message=exc.message,
            error_code=exc.error_code
        ).model_dump()
    )


async def authorization_exception_handler(request: Request, exc: AuthorizationException):
    """Handle authorization exceptions (403)"""
    logger.warning(f"Authorization failed: {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content=ErrorResponse(
            status="error",
            message=exc.message,
            error_code=exc.error_code
        ).model_dump()
    )


async def not_found_exception_handler(request: Request, exc: NotFoundException):
    """Handle not found exceptions (404)"""
    logger.info(f"Resource not found: {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=ErrorResponse(
            status="error",
            message=exc.message,
            error_code=exc.error_code
        ).model_dump()
    )


async def validation_exception_handler(request: Request, exc: ValidationException):
    """Handle validation exceptions (400)"""
    logger.warning(f"Validation error: {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=ErrorResponse(
            status="error",
            message=exc.message,
            error_code=exc.error_code
        ).model_dump()
    )


async def conflict_exception_handler(request: Request, exc: ConflictException):
    """Handle conflict exceptions (409)"""
    logger.warning(f"Conflict error: {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=ErrorResponse(
            status="error",
            message=exc.message,
            error_code=exc.error_code
        ).model_dump()
    )


async def patient_fhir_exception_handler(request: Request, exc: PatientFHIRException):
    """Handle PatientFHIR source exceptions (503)"""
    logger.error(f"PatientFHIR source error: {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=ErrorResponse(
            status="error",
            message=exc.message,
            error_code=exc.error_code
        ).model_dump()
    )


async def unhandled_exception_handler(request: Request, exc: Exception):
    """Log unexpected failures with request context and return a stable API error."""
    logger.exception(
        "Unhandled API error for %s %s",
        request.method,
        request.url.path,
        exc_info=exc,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            status="error",
            message="An unexpected server error occurred. Check the backend logs for details.",
            error_code="INTERNAL_SERVER_ERROR",
        ).model_dump(),
    )


def register_exception_handlers(app):
    """Register all exception handlers with FastAPI app"""
    app.add_exception_handler(AuthenticationException, authentication_exception_handler)
    app.add_exception_handler(AuthorizationException, authorization_exception_handler)
    app.add_exception_handler(NotFoundException, not_found_exception_handler)
    app.add_exception_handler(ValidationException, validation_exception_handler)
    app.add_exception_handler(ConflictException, conflict_exception_handler)
    app.add_exception_handler(PatientFHIRException, patient_fhir_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
    
    logger.info("Global exception handlers registered")
