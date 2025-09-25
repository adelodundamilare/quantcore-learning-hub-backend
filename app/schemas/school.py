from pydantic import BaseModel, ConfigDict

class SchoolBase(BaseModel):
    """Base schema for a school."""
    name: str

class SchoolCreate(SchoolBase):
    """Schema for creating a school."""
    pass

class SchoolUpdate(SchoolBase):
    """Schema for updating a school."""
    name: str | None = None

class School(SchoolBase):
    """Schema for reading a school, includes the ID."""
    id: int

    class Config:
        from_attributes = True
