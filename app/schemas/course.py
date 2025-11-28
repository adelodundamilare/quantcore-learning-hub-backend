from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field, computed_field
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from app.core.constants import CourseLevelEnum
from app.models.course_enrollment import EnrollmentStatusEnum

class CourseBase(BaseModel):
    title: str
    description: Optional[str] = None
    thumbnail: Optional[str] = None
    level: CourseLevelEnum = Field(default=CourseLevelEnum.BEGINNER)
    is_active: bool = True

    model_config = ConfigDict(use_enum_values=True)

class CourseCreate(CourseBase):
    school_id: Optional[int] = None

class CourseUpdate(CourseBase):
    title: Optional[str] = None
    description: Optional[str] = None
    thumbnail: Optional[str] = None
    level: Optional[CourseLevelEnum] = None
    is_active: Optional[bool] = None

class Course(CourseBase):
    id: int
    school_id: int
    total_enrolled_students: int = 0
    user_progress_percentage: Optional[int] = None
    user_enrollment_status: Optional[EnrollmentStatusEnum] = None
    user_started_at: Optional[datetime] = None
    user_completed_at: Optional[datetime] = None
    curriculums: List[dict] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def average_rating(self) -> float:
        return 0.0
