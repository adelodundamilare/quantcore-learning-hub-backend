from pydantic import BaseModel, EmailStr
from typing import List

class SchoolReportSchema(BaseModel):
    total_courses_count: int
    total_enrolled_students_count: int

class LeaderboardEntrySchema(BaseModel):
    student_id: int
    student_full_name: str
    student_email: EmailStr
    lessons_completed: int
    accumulated_exam_score: float
    total_rewards: int

class LeaderboardResponseSchema(BaseModel):
    items: List[LeaderboardEntrySchema]
    total: int
    skip: int
    limit: int
