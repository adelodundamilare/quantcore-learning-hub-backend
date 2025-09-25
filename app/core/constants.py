from enum import Enum


class RoleEnum(str, Enum):
    SUPER_ADMIN = "Super Admin"
    SCHOOL_ADMIN = "School Admin"
    TEACHER = "Teacher"
    STUDENT = "Student"
    ADMIN = "Admin"
    MEMBER = "Member"

class PermissionEnum(str, Enum):
    # User Permissions
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"

    # School Permissions
    SCHOOL_CREATE = "school:create"
    SCHOOL_READ = "school:read"
    SCHOOL_UPDATE = "school:update"
    SCHOOL_DELETE = "school:delete"

    # Role Permissions
    ROLE_CREATE = "role:create"
    ROLE_READ = "role:read"
    ROLE_UPDATE = "role:update"
    ROLE_DELETE = "role:delete"

    # Permission Permissions
    PERMISSION_ASSIGN = "permission:assign"
    PERMISSION_CREATE = "permission:create"
    PERMISSION_READ = "permission:read"

