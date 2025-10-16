from pydantic import BaseModel, ConfigDict
from typing import Optional, Any
from datetime import datetime

class UserAnswerBase(BaseModel):
    exam_attempt_id: int
    question_id: int
    answer_text: Optional[int] = None # Stores the index of the user's chosen option
    user_id: Optional[int] = None

    is_correct: Optional[bool] = None
    score: Optional[float] = None

class UserAnswerCreate(UserAnswerBase):
    pass

class UserAnswerUpdate(UserAnswerBase):
    exam_attempt_id: Optional[int] = None
    question_id: Optional[int] = None
    answer_text: Optional[int] = None
    is_correct: Optional[bool] = None
    score: Optional[float] = None

class UserAnswer(UserAnswerBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)
