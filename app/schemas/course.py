from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from app.core.constants import CourseLevelEnum
from app.schemas.user import User

class CourseBase(BaseModel):
    """Base schema for a course."""
    title: str
    description: Optional[str] = None
    thumbnail: Optional[str] = None
    level: CourseLevelEnum = Field(default=CourseLevelEnum.BEGINNER)
    is_active: bool = True

class CourseCreate(CourseBase):
    """Schema for creating a course."""
    school_id: Optional[int] = None # Optional for School Admin, required for Super Admin

class CourseUpdate(CourseBase):
    """Schema for updating a course."""
    title: Optional[str] = None
    description: Optional[str] = None
    thumbnail: Optional[str] = None
    level: Optional[CourseLevelEnum] = None
    is_active: Optional[bool] = None

class Course(CourseBase):
    """Schema for reading a course, includes ID and relationships."""
    id: int
    school_id: int
    # teachers: List[User] = []
    # students: List[User] = []
    model_config = ConfigDict(from_attributes=True)
