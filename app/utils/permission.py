from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.course import Course
from app.schemas.user import UserContext
from app.core.constants import RoleEnum
from app.crud.role import role as crud_role
from app.crud.user import user as crud_user


class PermissionHelper:
    @staticmethod
    def is_super_admin(context: UserContext) -> bool:
        return context.role.name == RoleEnum.SUPER_ADMIN # or admin or member

    @staticmethod
    def is_school_admin(context: UserContext) -> bool:
        return context.role.name == RoleEnum.SCHOOL_ADMIN

    @staticmethod
    def is_teacher(context: UserContext) -> bool:
        return context.role.name == RoleEnum.TEACHER

    @staticmethod
    def is_student(context: UserContext) -> bool:
        return context.role.name == RoleEnum.STUDENT

    @staticmethod
    def is_teacher_of_course(user: User, course: Course) -> bool:
        return user.id in [teacher.id for teacher in course.teachers]

    @staticmethod
    def is_student_of_course(user: User, course: Course) -> bool:
        return user.id in [student.id for student in course.students]

    @staticmethod
    def belongs_to_school(context: UserContext, school_id: int) -> bool:
        return context.school and context.school.id == school_id

    @staticmethod
    def can_manage_school_resources(context: UserContext, school_id: int) -> bool:
        if PermissionHelper.is_super_admin(context):
            return True
        return PermissionHelper.belongs_to_school(context, school_id) and (
            PermissionHelper.is_school_admin(context) or PermissionHelper.is_teacher(context)
        )

    @staticmethod
    def can_view_school_resources(context: UserContext, school_id: int) -> bool:
        if PermissionHelper.is_super_admin(context):
            return True
        return PermissionHelper.belongs_to_school(context, school_id)

    @staticmethod
    def can_manage_course(context: UserContext, course: Course) -> bool:
        if PermissionHelper.is_super_admin(context):
            return True
        if not PermissionHelper.belongs_to_school(context, course.school_id):
            return False
        if PermissionHelper.is_school_admin(context):
            return True
        if PermissionHelper.is_teacher(context) and PermissionHelper.is_teacher_of_course(context.user, course):
            return True
        return False

    @staticmethod
    def can_view_course(context: UserContext, course: Course) -> bool:
        if PermissionHelper.is_super_admin(context):
            return True
        if not PermissionHelper.belongs_to_school(context, course.school_id):
            return False
        if PermissionHelper.is_school_admin(context):
            return True
        if PermissionHelper.is_teacher(context) and PermissionHelper.is_teacher_of_course(context.user, course):
            return True
        if PermissionHelper.is_student(context) and PermissionHelper.is_student_of_course(context.user, course):
            return True
        return False

    @staticmethod
    def require_not_student(context: UserContext, error_message: str = "Students cannot perform this action."):
        if PermissionHelper.is_student(context):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error_message)

    @staticmethod
    def require_course_management_permission(context: UserContext, course: Course):
        if not PermissionHelper.can_manage_course(context, course):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to manage this course."
            )

    @staticmethod
    def require_course_view_permission(context: UserContext, course: Course):
        if not PermissionHelper.can_view_course(context, course):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view this course."
            )

    @staticmethod
    def require_school_management_permission(context: UserContext, school_id: int):
        if not PermissionHelper.can_manage_school_resources(context, school_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to manage resources in this school."
            )

    @staticmethod
    def require_school_view_permission(context: UserContext, school_id: int):
        if not PermissionHelper.can_view_school_resources(context, school_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view resources in this school."
            )

    @staticmethod
    def validate_user_role_in_school(db: Session, user_id: int, school_id: int, role_name: RoleEnum):
        role = crud_role.get_by_name(db, name=role_name)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"{role_name.value} role not found."
            )

        association = crud_user.get_association_by_user_school_role(
            db, user_id=user_id, school_id=school_id, role_id=role.id
        )
        if not association:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User does not have {role_name.value} role in this school."
            )

    @staticmethod
    def get_school_id_for_operation(context: UserContext, provided_school_id: Optional[int]) -> int:
        if PermissionHelper.is_super_admin(context):
            if not provided_school_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Super Admin must specify school_id."
                )
            return provided_school_id
        else:
            if not context.school:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User must be assigned to a school to perform this operation."
                )
            if provided_school_id and provided_school_id != context.school.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only perform operations for your assigned school."
                )
            return context.school.id


permission_helper = PermissionHelper()