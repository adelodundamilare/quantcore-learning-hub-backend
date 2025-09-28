from pydantic import BaseModel, field_validator
from typing import List
from .user import UserContext
from pydantic import EmailStr

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenPayload(BaseModel):
    user_id: int | None = None
    school_id: int | None = None
    role_id: int | None = None
    jti: str | None = None
    exp: int | None = None

class LoginResponse(BaseModel):
    """Response for the login endpoint."""
    token: Token
    contexts: List[UserContext] = []
    class Config:
        from_attributes = True

class ForgotPasswordRequest(BaseModel):
    email: EmailStr
    frontend_base_url: str

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class VerifyAccountRequest(BaseModel):
    email: EmailStr
    code: str

class ResendVerificationRequest(BaseModel):
    email: EmailStr

class SuperAdminCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str

    @field_validator("password")
    def validate_password(cls, v):
        if not v or not v.strip():
            raise ValueError("Password cannot be empty or contain only whitespace.")
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        return v