from pydantic import BaseModel, ConfigDict

class PermissionBase(BaseModel):
    """Base schema for a permission."""
    name: str
    description: str | None = None

class PermissionCreate(PermissionBase):
    """Schema for creating a permission."""
    pass

class PermissionUpdate(PermissionBase):
    """Schema for updating a permission."""
    name: str | None = None # Allow optional updates

class Permission(PermissionBase):
    """Schema for reading a permission, includes the ID."""
    id: int
    model_config = ConfigDict(from_attributes=True)
