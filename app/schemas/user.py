from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict, model_validator
from typing import Optional, Any, List

from .school import School
from .role import Role
from app.core.constants import RoleEnum

class UserBase(BaseModel):
    """Base user schema with common fields."""
    full_name: str
    email: EmailStr
    avatar: Optional[str] = None

class UserCreate(UserBase):
    """Schema for creating a new user, includes password."""
    password: str

    @field_validator("password")
    def validate_password(cls, v):
        if not v or not v.strip():
            raise ValueError("Password cannot be empty or contain only whitespace.")
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        return v

class UserUpdate(BaseModel):
    """Schema for updating a user's profile."""
    full_name: Optional[str] = None
    avatar: Optional[str] = None

    @field_validator("full_name")
    def not_empty(cls, v):
        if v is not None and not v.strip():
            raise ValueError("Full name cannot be empty")
        return v

    @model_validator(mode='before')
    @classmethod
    def at_least_one_value(cls, data: Any):
        if isinstance(data, dict) and not any(data.values()):
            raise ValueError("At least one field must be provided for update")
        return data

class User(UserBase):
    """Main user schema for reading user data."""
    id: int
    is_active: bool
    # is_verified: bool
    auth_provider: str
    model_config = ConfigDict(from_attributes=True)

class UserContext(BaseModel):
    """Represents a user's role within a specific school."""
    school: School
    role: Role
    model_config = ConfigDict(from_attributes=True)

class UserInvite(BaseModel):
    """Schema for inviting a new user to a school."""
    full_name: str
    email: EmailStr
    role_name: RoleEnum

    class Config:
        schema_extra = {
            "properties": {
                "role_name": {
                    "enum": ["teacher", "student", "admin", "super_admin"],
                    "description": "Role to assign to the invited user"
                }
            },
            "example": {
                "full_name": "Student",
                "email": "user@example.com",
                "role_name": "student"
            }
        }

    @field_validator('role_name')
    def validate_role(cls, v):
        if v not in [RoleEnum.TEACHER, RoleEnum.STUDENT]:
            raise ValueError("Users can only be invited as a Teacher or a Student.")
        return v