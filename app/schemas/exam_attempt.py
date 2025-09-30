from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime

from app.core.constants import ExamAttemptStatusEnum
from app.schemas.user_answer import UserAnswer

class ExamAttemptBase(BaseModel):
    user_id: int
    exam_id: int
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    score: Optional[float] = None
    passed: Optional[bool] = None
    status: ExamAttemptStatusEnum = Field(default=ExamAttemptStatusEnum.IN_PROGRESS)

class ExamAttemptCreate(ExamAttemptBase):
    pass

class ExamAttemptUpdate(ExamAttemptBase):
    user_id: Optional[int] = None
    exam_id: Optional[int] = None
    end_time: Optional[datetime] = None
    score: Optional[float] = None
    passed: Optional[bool] = None
    status: Optional[ExamAttemptStatusEnum] = None

class ExamAttempt(ExamAttemptBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]
    user_answers: List[UserAnswer] = []

    model_config = ConfigDict(from_attributes=True)
