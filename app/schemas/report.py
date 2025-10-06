from pydantic import BaseModel

class SchoolReportSchema(BaseModel):
    total_courses_count: int
    total_enrolled_students_count: int
