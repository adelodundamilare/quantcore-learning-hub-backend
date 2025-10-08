from pydantic import BaseModel, ConfigDict, EmailStr
from typing import List

class SchoolBase(BaseModel):
    name: str

class SchoolCreate(SchoolBase):
    pass

class SchoolUpdate(SchoolBase):
    name: str | None = None

class School(SchoolBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class AdminSchoolDataSchema(BaseModel):
    school_id: int
    school_name: str
    creator_name: str
    creator_email: str
    total_teachers: int
    total_students: int
    is_active: bool
