from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class LessonProgressBase(BaseModel):
    enrollment_id: int
    lesson_id: int


class LessonProgressCreate(LessonProgressBase):
    started_at: Optional[datetime] = None
    last_accessed_at: Optional[datetime] = None


class LessonProgressUpdate(BaseModel):
    is_completed: Optional[bool] = None
    completed_at: Optional[datetime] = None
    time_spent_seconds: Optional[int] = None
    last_accessed_at: Optional[datetime] = None


class LessonProgress(LessonProgressBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    is_completed: bool
    time_spent_seconds: int
    last_accessed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None