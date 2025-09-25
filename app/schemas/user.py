from pydantic import BaseModel, EmailStr, field_validator, model_validator
from typing import Optional, Any

class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str

    @field_validator("password")
    def validate_password(cls, v):
        if not v or not v.strip():
            raise ValueError("Password cannot be empty or contain only whitespace.")
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        return v

class UserUpdate(BaseModel):
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

class UserResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    auth_provider: str
    is_verified: bool
    avatar: Optional[str]

    class Config:
        from_attributes = True