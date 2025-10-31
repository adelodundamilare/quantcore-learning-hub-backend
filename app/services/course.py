from typing import List
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.course import Course as CourseModel
from app.schemas.course import CourseCreate, CourseUpdate, Course as CourseSchema
from app.schemas.user import UserContext, User
from app.core.constants import RoleEnum
from app.crud.user import user as crud_user
from app.crud.school import school as crud_school
from app.crud.course import course as crud_course
from app.crud.course_enrollment import course_enrollment as crud_enrollment
from app.services.notification import notification_service
from app.utils.permission import PermissionHelper as permission_helper
from app.schemas.course_enrollment import CourseEnrollmentCreate
from app.models.course_enrollment import EnrollmentStatusEnum


class CourseService:

    def create_course(self, db: Session, course_in: CourseCreate, current_user_context: UserContext) -> CourseSchema:
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

        teacher_user = crud_user.get(db, id=current_user_context.user.id)
        if not teacher_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher user not found.")

        if permission_helper.is_teacher(current_user_context):
            crud_course.add_teacher_to_course(db, course=new_course, user=teacher_user)

        db.flush()

        notification_service.create_notification(
            db,
            user_id=current_user_context.user.id,
            message=f"Course '{new_course.title}' created successfully.",
            notification_type="course_creation",
            link=f"/courses/{new_course.id}"
        )

        return CourseSchema.model_validate(new_course)

    def update_course(self, db: Session, course_id: int, course_in: CourseUpdate, current_user_context: UserContext) -> CourseSchema:
        course = crud_course.get(db, id=course_id)
        if not course:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")

        permission_helper.require_course_management_permission(current_user_context, course)

        updated_course = crud_course.update(db, db_obj=course, obj_in=course_in)
        return CourseSchema.model_validate(updated_course)

    def delete_course(self, db: Session, course_id: int, current_user_context: UserContext) -> CourseSchema:
        course = crud_course.get(db, id=course_id)
        if not course:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")

        permission_helper.require_course_management_permission(current_user_context, course)

        deleted_course = crud_course.remove(db, id=course_id)
        return CourseSchema.model_validate(deleted_course)

    def assign_teacher(self, db: Session, course_id: int, user_id: int, current_user_context: UserContext) -> CourseSchema:
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

        return CourseSchema.model_validate(course)

    def remove_teacher(self, db: Session, course_id: int, user_id: int, current_user_context: UserContext) -> CourseSchema:
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

        return CourseSchema.model_validate(course)

    def enroll_student(self, db: Session, course_id: int, user_id: int, current_user_context: UserContext) -> CourseSchema:
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

        enrollment_in = CourseEnrollmentCreate(
            user_id=user_id,
            course_id=course_id,
            status=EnrollmentStatusEnum.NOT_STARTED,
            progress_percentage=0
        )
        crud_enrollment.create(db, obj_in=enrollment_in)

        notification_service.create_notification(
            db,
            user_id=student_user.id,
            message=f"You have been enrolled in course '{course.title}'.",
            notification_type="course_enrollment",
            link=f"/courses/{course.id}"
        )

        return CourseSchema.model_validate(course)

    def unenroll_student(self, db: Session, course_id: int, user_id: int, current_user_context: UserContext) -> CourseSchema:
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

        enrollment = crud_enrollment.get_by_user_and_course(db, user_id=user_id, course_id=course_id)
        if enrollment:
            crud_enrollment.remove(db, id=enrollment.id)

        notification_service.create_notification(
            db,
            user_id=student_user.id,
            message=f"You have been unenrolled from course '{course.title}'.",
            notification_type="course_unenrollment",
            link=f"/courses/{course.id}"
        )

        return CourseSchema.model_validate(course)

    def _enrich_course_with_progress(self, db: Session, course_model: CourseModel, user_id: int) -> CourseSchema:
        course_schema = CourseSchema.model_validate(course_model)

        user_enrollment = next((e for e in course_model.enrollments if e.user_id == user_id), None)

        if user_enrollment:
            course_schema.user_progress_percentage = user_enrollment.progress_percentage
            course_schema.user_enrollment_status = user_enrollment.status
            course_schema.user_started_at = user_enrollment.started_at
            course_schema.user_completed_at = user_enrollment.completed_at

            lesson_progress_map = {lp.lesson_id: lp for lp in user_enrollment.lesson_progress}

            for curriculum_schema in course_schema.curriculums:
                for lesson_schema in curriculum_schema.lessons:
                    lesson_progress = lesson_progress_map.get(lesson_schema.id)
                    if lesson_progress:
                        lesson_schema.is_completed = lesson_progress.is_completed
                        lesson_schema.started_at = lesson_progress.started_at
                        lesson_schema.completed_at = lesson_progress.completed_at
                        lesson_schema.time_spent_seconds = lesson_progress.time_spent_seconds
                        lesson_schema.last_accessed_at = lesson_progress.last_accessed_at
                    else:
                        lesson_schema.is_completed = False
                        lesson_schema.started_at = None
                        lesson_schema.completed_at = None
                        lesson_schema.time_spent_seconds = 0
                        lesson_schema.last_accessed_at = None
        else:
            course_schema.user_progress_percentage = 0
            course_schema.user_enrollment_status = EnrollmentStatusEnum.NOT_STARTED
            course_schema.user_started_at = None
            course_schema.user_completed_at = None
            for curriculum_schema in course_schema.curriculums:
                for lesson_schema in curriculum_schema.lessons:
                    lesson_schema.is_completed = False
                    lesson_schema.started_at = None
                    lesson_schema.completed_at = None
                    lesson_schema.time_spent_seconds = 0
                    lesson_schema.last_accessed_at = None

        return course_schema

    def get_course(self, db: Session, course_id: int, current_user_context: UserContext) -> CourseSchema:
        course_model = crud_course.get(db, id=course_id)
        if not course_model:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")

        permission_helper.require_course_view_permission(current_user_context, course_model)

        return self._enrich_course_with_progress(db, course_model, current_user_context.user.id)

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

    def get_all_courses(self, db: Session, current_user_context: UserContext, skip: int = 0, limit: int = 100) -> List[CourseSchema]:
        if permission_helper.is_super_admin(current_user_context):
            courses = crud_course.get_multi(db, skip=skip, limit=limit)
        elif current_user_context.school:
            courses = crud_course.get_courses_by_school(db, school_id=current_user_context.school.id, skip=skip, limit=limit)
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view courses.")

        enriched_courses = []
        for course_model in courses:
            enriched_courses.append(self._enrich_course_with_progress(db, course_model, current_user_context.user.id))
        return enriched_courses

    def get_user_courses(self, db: Session, current_user_context: UserContext) -> List[CourseSchema]:
        courses = crud_course.get_courses_by_user_id(db, user_id=current_user_context.user.id)
        enriched_courses = []
        for course_model in courses:
            enriched_courses.append(self._enrich_course_with_progress(db, course_model, current_user_context.user.id))
        return enriched_courses

    def get_courses_by_school_id(self, db: Session, school_id: int, current_user_context: UserContext, skip: int = 0, limit: int = 100) -> List[CourseSchema]:
        permission_helper.require_school_view_permission(current_user_context, school_id)
        courses = crud_course.get_courses_by_school(db, school_id=school_id, skip=skip, limit=limit)
        enriched_courses = []
        for course_model in courses:
            enriched_courses.append(self._enrich_course_with_progress(db, course_model, current_user_context.user.id))
        return enriched_courses


course_service = CourseService()