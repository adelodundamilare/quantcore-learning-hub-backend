from enum import Enum


class RoleEnum(str, Enum):
    SUPER_ADMIN = "Super Admin"
    SCHOOL_ADMIN = "School Admin"
    TEACHER = "Teacher"
    STUDENT = "Student"
    ADMIN = "Admin"
    MEMBER = "Member"
