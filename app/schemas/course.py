from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime
from app.core.constants import CourseLevelEnum
from app.schemas.user import User
from app.schemas.curriculum import Curriculum
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
    total_enrolled_students: int = 0 # Added for dynamic retrieval
    average_rating: float = 0.0 # Added for dynamic retrieval
    user_progress_percentage: Optional[int] = None
    user_enrollment_status: Optional[EnrollmentStatusEnum] = None
    user_started_at: Optional[datetime] = None
    user_completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
    curriculums: List[Curriculum] = []
