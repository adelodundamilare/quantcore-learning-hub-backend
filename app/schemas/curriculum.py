from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List

from app.schemas.lesson import Lesson

class CurriculumBase(BaseModel):
    title: str
    description: Optional[str] = None
    order: int = Field(default=0)

class CurriculumCreate(CurriculumBase):
    course_id: int

class CurriculumUpdate(CurriculumBase):
    title: Optional[str] = None
    description: Optional[str] = None
    order: Optional[int] = None

class Curriculum(CurriculumBase):
    id: int
    course_id: int
    lessons: List[Lesson] = []

    model_config = ConfigDict(from_attributes=True)
