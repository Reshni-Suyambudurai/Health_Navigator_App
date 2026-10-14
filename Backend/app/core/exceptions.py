"""
Custom exceptions for the application
"""

class BaseAPIException(Exception):
    """Base exception class for all API exceptions"""
    def __init__(self, message: str, error_code: str = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class AuthenticationException(BaseAPIException):
    """Raised when authentication fails (401 Unauthorized)"""
    def __init__(self, message: str = "Authentication failed", error_code: str = "AUTH_001"):
        super().__init__(message, error_code)


class AuthorizationException(BaseAPIException):
    """Raised when user is not authorized (403 Forbidden)"""
    def __init__(self, message: str = "Access forbidden", error_code: str = "AUTH_002"):
        super().__init__(message, error_code)


class NotFoundException(BaseAPIException):
    """Raised when resource is not found (404 Not Found)"""
    def __init__(self, message: str = "Resource not found", error_code: str = "NOT_FOUND"):
        super().__init__(message, error_code)


class ValidationException(BaseAPIException):
    """Raised when validation fails (400 Bad Request)"""
    def __init__(self, message: str = "Validation error", error_code: str = "VALIDATION_ERROR"):
        super().__init__(message, error_code)


class ConflictException(BaseAPIException):
    """Raised when there's a conflict (409 Conflict)"""
    def __init__(self, message: str = "Resource conflict", error_code: str = "CONFLICT"):
        super().__init__(message, error_code)
