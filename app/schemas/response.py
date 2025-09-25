from pydantic import BaseModel, Field
from typing import Generic, TypeVar, Optional

DataType = TypeVar("DataType")

class APIResponse(BaseModel, Generic[DataType]):
    """Generic API response model for consistent output."""
    message: str = Field(..., description="A human-readable message about the response.")
    data: Optional[DataType] = Field(None, description="The actual data returned by the API, if any.")
