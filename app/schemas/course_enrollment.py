from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from app.models.course_enrollment import EnrollmentStatusEnum


class CourseEnrollmentBase(BaseModel):
    user_id: int
    course_id: int
    status: Optional[EnrollmentStatusEnum] = EnrollmentStatusEnum.NOT_STARTED


class CourseEnrollmentCreate(CourseEnrollmentBase):
    pass


class CourseEnrollmentUpdate(BaseModel):
    status: Optional[EnrollmentStatusEnum] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress_percentage: Optional[int] = None


class CourseEnrollment(CourseEnrollmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress_percentage: int
    created_at: datetime
    updated_at: Optional[datetime] = None