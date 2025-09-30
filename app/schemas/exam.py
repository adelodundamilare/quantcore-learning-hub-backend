from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime

from app.schemas.question import Question
from app.schemas.exam_attempt import ExamAttempt

class ExamBase(BaseModel):
    title: str
    description: Optional[str] = None
    course_id: Optional[int] = None
    curriculum_id: Optional[int] = None
    duration_minutes: Optional[int] = None
    pass_percentage: Optional[float] = None
    is_active: bool = True
    allow_multiple_attempts: bool = False
    show_results_immediately: bool = False

class ExamCreate(ExamBase):
    pass

class ExamUpdate(ExamBase):
    title: Optional[str] = None
    is_active: Optional[bool] = None

class Exam(ExamBase):
    id: int
    created_at: datetime
    updated_at: datetime
    questions: List[Question] = []
    attempts: List[ExamAttempt] = []

    model_config = ConfigDict(from_attributes=True)
