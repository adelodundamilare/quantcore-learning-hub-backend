from pydantic import BaseModel, ConfigDict
from .permission import Permission

class RoleBase(BaseModel):
    """Base schema for a role."""
    name: str
    description: str | None = None

class RoleCreate(RoleBase):
    """Schema for creating a role."""
    pass

class RoleUpdate(RoleBase):
    """Schema for updating a role."""
    name: str | None = None
    description: str | None = None

class Role(RoleBase):
    """Schema for reading a role, includes ID and permissions."""
    id: int
    permissions: list[Permission] = []
    model_config = ConfigDict(from_attributes=True)
