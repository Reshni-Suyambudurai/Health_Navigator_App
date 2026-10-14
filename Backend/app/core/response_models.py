"""
Standardized response formats for success and error responses
"""

from pydantic import BaseModel
from typing import Any, Optional


class SuccessResponse(BaseModel):
    """Standard success response format"""
    status: str = "success"
    message: str
    data: Optional[Any] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "Operation completed successfully",
                "data": {"id": 1, "name": "John Doe"}
            }
        }


class ErrorResponse(BaseModel):
    """Standard error response format"""
    status: str = "error"
    message: str
    error_code: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "error",
                "message": "Authentication failed",
                "error_code": "AUTH_001"
            }
        }
