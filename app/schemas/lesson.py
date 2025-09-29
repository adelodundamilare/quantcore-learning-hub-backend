from pydantic import BaseModel, ConfigDict, Field
from typing import Optional

from app.core.constants import LessonTypeEnum

class LessonBase(BaseModel):
    title: str
    content: Optional[str] = None
    lesson_type: LessonTypeEnum = Field(default=LessonTypeEnum.TEXT)
    order: int = Field(default=0)

class LessonCreate(LessonBase):
    curriculum_id: int

class LessonUpdate(LessonBase):
    title: Optional[str] = None
    content: Optional[str] = None
    lesson_type: Optional[LessonTypeEnum] = None
    order: Optional[int] = None

class Lesson(LessonBase):
    id: int
    curriculum_id: int

    model_config = ConfigDict(from_attributes=True)
