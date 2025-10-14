from enum import Enum


ADMIN_SCHOOL_NAME = "ADM-SCH-PLAT-001"
class RoleEnum(str, Enum):
    SUPER_ADMIN = "super_admin"
    SCHOOL_ADMIN = "school_admin"
    TEACHER = "teacher"
    STUDENT = "student"
    ADMIN = "admin"
    MEMBER = "member"

class PermissionEnum(str, Enum):
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"

    SCHOOL_CREATE = "school:create"
    SCHOOL_READ = "school:read"
    SCHOOL_UPDATE = "school:update"
    SCHOOL_DELETE = "school:delete"

    ROLE_CREATE = "role:create"
    ROLE_READ = "role:read"
    ROLE_UPDATE = "role:update"
    ROLE_DELETE = "role:delete"

    PERMISSION_ASSIGN = "permission:assign"
    PERMISSION_CREATE = "permission:create"
    PERMISSION_READ = "permission:read"

    USER_INVITE = "user:invite"
    USER_MANAGE_ROLES = "user:manage_roles"
    USER_MANAGE_SCHOOLS = "user:manage_schools"

    COURSE_CREATE = "course:create"
    COURSE_READ_ALL = "course:read_all"
    COURSE_READ_OWN = "course:read_own"
    COURSE_UPDATE = "course:update"
    COURSE_DELETE = "course:delete"
    COURSE_ASSIGN_TEACHER = "course:assign_teacher"
    COURSE_ENROLL_STUDENT = "course:enroll_student"

class CourseLevelEnum(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    ALL = "all"

class LessonTypeEnum(str, Enum):
    TEXT = "text"
    VIDEO = "video"
    QUIZ = "quiz"

class QuestionTypeEnum(str, Enum):
    MULTIPLE_CHOICE = "multiple_choice"
    TRUE_FALSE = "true_false"

class ExamAttemptStatusEnum(str, Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    GRADED = "graded"

class EnrollmentStatusEnum(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DROPPED = "dropped"

class OrderTypeEnum(str, Enum):
    BUY = "buy"
    SELL = "sell"

class OrderStatusEnum(str, Enum):
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"

class StudentExamStatusEnum(str, Enum):
    LOCKED = "locked"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"