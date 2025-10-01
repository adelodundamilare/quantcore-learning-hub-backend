from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Any
from datetime import datetime

from app.core.constants import QuestionTypeEnum
from app.schemas.user_answer import UserAnswer

class QuestionBase(BaseModel):
    exam_id: int
    question_text: str
    question_type: QuestionTypeEnum
    options: Optional[List[str]] = None
    correct_answer: Optional[int] = None # Stores the index of the correct option
    points: int = Field(default=1)

    model_config = ConfigDict(use_enum_values=True)

class QuestionCreate(QuestionBase):
    pass

class QuestionUpdate(QuestionBase):
    question_text: Optional[str] = None
    question_type: Optional[QuestionTypeEnum] = None
    options: Optional[List[str]] = None
    correct_answer: Optional[int] = None
    points: Optional[int] = None

class Question(QuestionBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]
    user_answers: List[UserAnswer] = []

    model_config = ConfigDict(from_attributes=True)

class QuestionWithCorrectAnswer(Question):
    # This schema is for teachers/admins who need to see the correct answer
    pass
