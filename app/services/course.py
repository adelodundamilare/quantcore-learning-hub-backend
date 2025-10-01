from typing import List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.course import Course
from app.schemas.course import CourseCreate, CourseUpdate
from app.schemas.user import UserContext, User
from app.core.constants import RoleEnum
from app.crud.user import user as crud_user
from app.crud.school import school as crud_school
from app.crud.course import course as crud_course
from app.services.notification import notification_service
from app.utils.permission import PermissionHelper as permission_helper


class CourseService:

    def create_course(self, db: Session, course_in: CourseCreate, current_user_context: UserContext) -> Course:
        permission_helper.require_not_student(current_user_context, "Students cannot create courses.")

        school_id_for_course = permission_helper.get_school_id_for_operation(
            current_user_context,
            course_in.school_id
        )

        school = crud_school.get(db, id=school_id_for_course)
        if not school:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="School not found.")

        course_data = course_in.model_dump(exclude_unset=True)
        course_data['school_id'] = school_id_for_course
        new_course = crud_course.create(db, obj_in=course_data)

        if permission_helper.is_teacher(current_user_context):
            crud_course.add_teacher_to_course(db, course=new_course, user=current_user_context.user)

        db.flush()

        notification_service.create_notification(
            db,
            user_id=current_user_context.user.id,
            message=f"Course '{new_course.title}' created successfully.",
            notification_type="course_creation",
            link=f"/courses/{new_course.id}"
        )

        return new_course

    def update_course(self, db: Session, course_id: int, course_in: CourseUpdate, current_user_context: UserContext) -> Course:
        course = crud_course.get(db, id=course_id)
        if not course:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")

        permission_helper.require_course_management_permission(current_user_context, course)

        updated_course = crud_course.update(db, db_obj=course, obj_in=course_in)
        return updated_course

    def delete_course(self, db: Session, course_id: int, current_user_context: UserContext) -> Course:
        course = crud_course.get(db, id=course_id)
        if not course:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")

        permission_helper.require_course_management_permission(current_user_context, course)

        deleted_course = crud_course.remove(db, id=course_id)
        return deleted_course

    def assign_teacher(self, db: Session, course_id: int, user_id: int, current_user_context: UserContext) -> Course:
        course = crud_course.get(db, id=course_id)
        if not course:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")

        permission_helper.require_school_management_permission(current_user_context, course.school_id)

        teacher_user = crud_user.get(db, id=user_id)
        if not teacher_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher user not found.")

        permission_helper.validate_user_role_in_school(db, teacher_user.id, course.school.id, RoleEnum.TEACHER)

        if permission_helper.is_teacher_of_course(teacher_user, course):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User is already a teacher for this course.")

        crud_course.add_teacher_to_course(db, course=course, user=teacher_user)

        notification_service.create_notification(
            db,
            user_id=teacher_user.id,
            message=f"You have been assigned as a teacher to course '{course.title}'.",
            notification_type="course_assignment",
            link=f"/courses/{course.id}"
        )

        return course

    def remove_teacher(self, db: Session, course_id: int, user_id: int, current_user_context: UserContext) -> Course:
        course = crud_course.get(db, id=course_id)
        if not course:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")

        permission_helper.require_school_management_permission(current_user_context, course.school_id)

        teacher_user = crud_user.get(db, id=user_id)
        if not teacher_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher user not found.")

        if not permission_helper.is_teacher_of_course(teacher_user, course):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User is not a teacher for this course.")

        crud_course.remove_teacher_from_course(db, course=course, user=teacher_user)

        notification_service.create_notification(
            db,
            user_id=teacher_user.id,
            message=f"You have been removed as a teacher from course '{course.title}'.",
            notification_type="course_removal",
            link=f"/courses/{course.id}"
        )

        return course

    def enroll_student(self, db: Session, course_id: int, user_id: int, current_user_context: UserContext) -> Course:
        course = crud_course.get(db, id=course_id)
        if not course:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")

        permission_helper.require_school_management_permission(current_user_context, course.school_id)

        student_user = crud_user.get(db, id=user_id)
        if not student_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student user not found.")

        permission_helper.validate_user_role_in_school(db, student_user.id, course.school.id, RoleEnum.STUDENT)

        if permission_helper.is_student_of_course(student_user, course):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User is already enrolled in this course.")

        crud_course.enroll_student_in_course(db, course=course, user=student_user)

        notification_service.create_notification(
            db,
            user_id=student_user.id,
            message=f"You have been enrolled in course '{course.title}'.",
            notification_type="course_enrollment",
            link=f"/courses/{course.id}"
        )

        return course

    def unenroll_student(self, db: Session, course_id: int, user_id: int, current_user_context: UserContext) -> Course:
        course = crud_course.get(db, id=course_id)
        if not course:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")

        permission_helper.require_school_management_permission(current_user_context, course.school_id)

        student_user = crud_user.get(db, id=user_id)
        if not student_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student user not found.")

        if not permission_helper.is_student_of_course(student_user, course):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User is not enrolled in this course.")

        crud_course.unenroll_student_from_course(db, course=course, user=student_user)

        notification_service.create_notification(
            db,
            user_id=student_user.id,
            message=f"You have been unenrolled from course '{course.title}'.",
            notification_type="course_unenrollment",
            link=f"/courses/{course.id}"
        )

        return course

    def get_course(self, db: Session, course_id: int, current_user_context: UserContext) -> Course:
        course = crud_course.get(db, id=course_id)
        if not course:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")

        permission_helper.require_course_view_permission(current_user_context, course)
        return course

    def get_course_teachers(self, db: Session, course_id: int, current_user_context: UserContext) -> List[User]:
        course = crud_course.get(db, id=course_id)
        if not course:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")

        permission_helper.require_course_view_permission(current_user_context, course)
        return course.teachers

    def get_course_students(self, db: Session, course_id: int, current_user_context: UserContext) -> List[User]:
        course = crud_course.get(db, id=course_id)
        if not course:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")

        permission_helper.require_course_view_permission(current_user_context, course)
        return course.students

    def get_all_courses(self, db: Session, current_user_context: UserContext, skip: int = 0, limit: int = 100) -> List[Course]:
        if permission_helper.is_super_admin(current_user_context):
            return crud_course.get_multi(db, skip=skip, limit=limit)
        elif current_user_context.school:
            return crud_course.get_courses_by_school(db, school_id=current_user_context.school.id, skip=skip, limit=limit)
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view courses.")

    def get_user_courses(self, db: Session, current_user_context: UserContext) -> List[Course]:
        return crud_course.get_courses_by_user_id(db, user_id=current_user_context.user.id)

    def get_courses_by_school_id(self, db: Session, school_id: int, current_user_context: UserContext, skip: int = 0, limit: int = 100) -> List[Course]:
        permission_helper.require_school_view_permission(current_user_context, school_id)
        return crud_course.get_courses_by_school(db, school_id=school_id, skip=skip, limit=limit)


course_service = CourseService()