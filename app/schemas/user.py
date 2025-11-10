from pydantic import BaseModel, EmailStr, field_validator, ConfigDict, model_validator
from typing import Optional, Any, List
from datetime import datetime

from app.schemas.billing import StripeCustomerSchema

from .school import School
from .role import Role
from app.core.constants import RoleEnum, CourseLevelEnum
from app.schemas.trading import TradingAccountSummary

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
    stripe_customer: Optional[StripeCustomerSchema] = None
    model_config = ConfigDict(from_attributes=True)

class StudentProfile(User):
    assigned_lessons_count: int
    trading_fund_balance: TradingAccountSummary
    level: Optional[CourseLevelEnum] = None

class TeacherProfile(User):
    """Schema for a teacher's profile, including the number of students taught."""
    num_students_taught: int

class UserContext(BaseModel):
    """Represents a user's role within a specific school."""
    school: School
    role: Role
    user: User
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

class UserInvite(BaseModel):
    email: EmailStr
    full_name: str
    role_name: RoleEnum
    course_ids: Optional[List[int]] = None
    level: Optional[CourseLevelEnum] = None

    model_config = ConfigDict(
        use_enum_values=True,
        json_schema_extra={
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
    )

    @field_validator('role_name')
    def validate_role(cls, v):
        if v not in [RoleEnum.TEACHER, RoleEnum.STUDENT]:
            raise ValueError("Users can only be invited as a Teacher or a Student.")
        return v


class PlatformUserInvite(BaseModel):
    """Schema for super admin inviting platform-level users (admin/member)."""
    email: EmailStr
    full_name: str
    role_name: RoleEnum

    model_config = ConfigDict(
        use_enum_values=True,
        json_schema_extra={
            "properties": {
                "role_name": {
                    "enum": ["admin", "member"],
                    "description": "Platform role to assign (admin or member)"
                }
            },
            "example": {
                "full_name": "Platform Admin",
                "email": "admin@example.com",
                "role_name": "admin"
            }
        }
    )

    @field_validator('role_name')
    def validate_platform_role(cls, v):
        if v not in [RoleEnum.ADMIN, RoleEnum.MEMBER]:
            raise ValueError("Platform users can only be invited as Admin or Member.")
        return v


class AdminSchoolInvite(BaseModel):
    """Schema for inviting a new user to a school."""
    full_name: str
    school_name: str
    email: EmailStr


class TeacherUpdate(BaseModel):
    level: CourseLevelEnum

class UserAdminUpdate(BaseModel):
    """Schema for administrative user updates."""
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None

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

class UserRoleUpdate(BaseModel):
    """Schema for updating a user's role within a school."""
    role_name: RoleEnum
    level: Optional[CourseLevelEnum] = None

    model_config = ConfigDict(
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "role_name": "teacher",
                "level": "intermediate"
            }
        }
    )

class UserStatusUpdate(BaseModel):
    """Schema for updating a user's active status."""
    is_active: bool

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "is_active": False
            }
        }
    )


class BulkInviteRequest(BaseModel):
    course_ids: Optional[List[int]] = None
    level: Optional[CourseLevelEnum] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "course_ids": [1, 2, 3],
                "level": "beginner"
            }
        }
    )


class BulkInviteResult(BaseModel):
    row_number: int
    email: str
    full_name: str
    role_name: RoleEnum
    status: str  # "success", "error", "skipped"
    message: str
    user_id: Optional[int] = None

    model_config = ConfigDict(use_enum_values=True)


class BulkInviteStatus(BaseModel):
    """Schema for bulk invite processing status."""
    task_id: str
    status: str  # "processing", "completed", "failed"
    total_rows: int
    processed_rows: int
    successful_invites: int
    failed_invites: int
    results: List[BulkInviteResult]
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    model_config = ConfigDict(use_enum_values=True)
