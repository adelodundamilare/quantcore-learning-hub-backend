from wsgiref.validate import validator
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional, List
from datetime import datetime
from app.core.constants import CourseLevelEnum, StudentExamStatusEnum

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

    @field_validator('course_id', 'curriculum_id')
    @classmethod
    def validate_ids(cls, v):
        if v == 0:
            return None
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Final Exam",
                "description": "End of course assessment",
                "course_id": 1,
                "curriculum_id": None,
                "duration_minutes": 60,
                "pass_percentage": 70.0,
                "is_active": True,
                "allow_multiple_attempts": False,
                "show_results_immediately": False
            }
        }

class ExamCreate(ExamBase):
    pass

class ExamUpdate(ExamBase):
    title: Optional[str] = None
    is_active: Optional[bool] = None

class Exam(ExamBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    level: Optional[CourseLevelEnum] = None
    status: Optional[StudentExamStatusEnum] = None
    grade: Optional[float] = 0
    questions: List[Question] = []
    attempts: List[ExamAttempt] = []

    model_config = ConfigDict(from_attributes=True)
