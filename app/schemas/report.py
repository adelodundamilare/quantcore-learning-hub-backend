from pydantic import BaseModel, EmailStr
from typing import List, Optional

class TopPerformerSchema(BaseModel):
    user_id: int
    full_name: str
    email: EmailStr
    accumulated_exam_score: float

class StudentExamStats(BaseModel):
    pending_exams: int
    overall_grade_percentage: float


class MostActiveUserSchema(BaseModel):
    user_id: int
    full_name: str
    email: EmailStr
    lessons_completed: int

class AdminDashboardReportSchema(BaseModel):
    total_courses_count: int
    total_schools_count: int
    total_students_count: int
class SchoolReportSchema(BaseModel):
    total_courses_count: int
    total_enrolled_students_count: int
    top_performer: Optional[TopPerformerSchema] = None
    most_active_user: Optional[MostActiveUserSchema] = None

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

class TradingLeaderboardEntrySchema(BaseModel):
    student_id: int
    student_full_name: str
    student_email: EmailStr
    starting_capital: float
    current_balance: float
    trading_profit: float

class TradingLeaderboardResponseSchema(BaseModel):
    items: List[TradingLeaderboardEntrySchema]
    total: int
    skip: int
    limit: int

class SchoolDashboardStatsSchema(BaseModel):
    total_students: int
    total_courses: int
    total_teams: int


class AdminDashboardStatsSchema(BaseModel):
    total_students: int
    total_teachers: int
    total_courses: int

