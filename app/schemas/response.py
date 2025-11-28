from pydantic import BaseModel, Field
from typing import Generic, TypeVar, Optional, Any, Dict

DataType = TypeVar("DataType")

class APIResponse(BaseModel, Generic[DataType]):
    """Generic API response model for consistent output."""
    message: str = Field(..., description="A human-readable message about the response.")
    data: Optional[DataType] = Field(None, description="The actual data returned by the API, if any.")

class ErrorDetail(BaseModel):
    """Standardized error detail model."""
    code: str = Field(..., description="Error code for client handling")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error context")

class ErrorResponse(BaseModel):
    """Standardized error response model."""
    error: ErrorDetail = Field(..., description="Error details")
    timestamp: str = Field(..., description="ISO 8601 timestamp of error")
    path: str = Field(..., description="Request path that caused the error")
    request_id: Optional[str] = Field(None, description="Unique request identifier for debugging")
