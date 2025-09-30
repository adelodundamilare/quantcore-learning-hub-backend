from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Any
from datetime import datetime

class UserAnswerBase(BaseModel):
    exam_attempt_id: int
    question_id: int
    answer_text: Optional[int] = None # Stores the index of the user's chosen option

    is_correct: Optional[bool] = None
    score: Optional[float] = None

class UserAnswerCreate(UserAnswerBase):
    pass

class UserAnswerUpdate(UserAnswerBase):
    answer_text: Optional[str] = None
    is_correct: Optional[bool] = None
    score: Optional[float] = None

class UserAnswer(UserAnswerBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
