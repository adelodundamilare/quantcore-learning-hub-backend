from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime

from app.core.constants import LessonTypeEnum

class LessonBase(BaseModel):
    title: str
    content: Optional[str] = None
    lesson_type: LessonTypeEnum = Field(default=LessonTypeEnum.TEXT)
    duration: int = Field(default=0) # Duration in minutes
    order: int = Field(default=0)

    model_config = ConfigDict(use_enum_values=True)

class LessonCreate(LessonBase):
    curriculum_id: int

class LessonUpdate(LessonBase):
    title: Optional[str] = None
    content: Optional[str] = None
    lesson_type: Optional[LessonTypeEnum] = None
    duration: Optional[int] = None
    order: Optional[int] = None

class Lesson(LessonBase):
    id: int
    curriculum_id: int
    is_completed: Optional[bool] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    time_spent_seconds: Optional[int] = None
    last_accessed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
