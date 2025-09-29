from typing import List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.crud.course import course as crud_course
from app.crud.user import user as crud_user
from app.crud.role import role as crud_role
from app.crud.school import school as crud_school
from app.schemas.course import CourseCreate, Course
from app.schemas.user import UserContext
from app.core.constants import RoleEnum
from app.services.notification import notification_service

class CourseService:
    """Service layer for course-related business logic."""

    def create_course(self, db: Session, course_in: CourseCreate, current_user_context: UserContext) -> Course:
        # Permission Logic
        if current_user_context.role.name == RoleEnum.STUDENT:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Students cannot create courses.")

        school_id_for_course = None
        if current_user_context.role.name == RoleEnum.SUPER_ADMIN:
            if not course_in.school_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Super Admin must specify school_id for the course.")
            school_id_for_course = course_in.school_id
        else:
            if not current_user_context.school:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User must be assigned to a school to create a course.")
            if course_in.school_id and course_in.school_id != current_user_context.school.id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only create courses for your assigned school.")
            school_id_for_course = current_user_context.school.id

        # Ensure the school exists
        school = crud_school.get(db, id=school_id_for_course)
        if not school:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="School not found.")

        course_data = course_in.model_dump(exclude_unset=True)
        course_data['school_id'] = school_id_for_course
        new_course = crud_course.create(db, obj_in=course_data, commit=False)

        # Auto-assign teacher if the creator is a teacher
        if current_user_context.role.name == RoleEnum.TEACHER:
            self.assign_teacher(db, course_id=new_course.id, user_id=current_user_context.user.id, current_user_context=current_user_context)

        notification_service.create_notification(
            db,
            user_id=current_user_context.user.id,
            message=f"Course '{new_course.title}' created successfully.",
            notification_type="course_creation",
            link=f"/courses/{new_course.id}"
        )
        return new_course
    def assign_teacher(self, db: Session, course_id: int, user_id: int, current_user_context: UserContext) -> Course:
        course = crud_course.get(db, id=course_id)
        if not course:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")

        # Check if current user has permission for this school
        if current_user_context.role.name != RoleEnum.SUPER_ADMIN and course.school_id != current_user_context.school.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only assign teachers to courses in your assigned school.")

        teacher_user = crud_user.get(db, id=user_id)
        if not teacher_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher user not found.")

        # Verify user has a teacher role in this school context
        teacher_role = crud_role.get_by_name(db, name=RoleEnum.TEACHER)
        if not teacher_role:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Teacher role not found.")

        teacher_association = crud_user.get_association_by_user_school_role(
            db, user_id=teacher_user.id, school_id=course.school.id, role_id=teacher_role.id
        )
        if not teacher_association:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User does not have a teacher role in this school.")

        if teacher_user in course.teachers:
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

    def enroll_student(self, db: Session, course_id: int, user_id: int, current_user_context: UserContext) -> Course:
        course = crud_course.get(db, id=course_id)
        if not course:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")

        # Check if current user has permission for this school
        if current_user_context.role.name != RoleEnum.SUPER_ADMIN and course.school_id != current_user_context.school.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only enroll students in courses in your assigned school.")

        student_user = crud_user.get(db, id=user_id)
        if not student_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student user not found.")

        student_role = crud_role.get_by_name(db, name=RoleEnum.STUDENT)
        if not student_role:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Student role not found.")

        student_association = crud_user.get_association_by_user_school_role(
            db, user_id=student_user.id, school_id=course.school.id, role_id=student_role.id
        )
        if not student_association:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User does not have a student role in this school.")

        if student_user in course.students:
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

    def get_all_courses(self, db: Session, current_user_context: UserContext, skip: int = 0, limit: int = 100) -> List[Course]:
        if current_user_context.role.name == RoleEnum.SUPER_ADMIN:
            return crud_course.get_multi(db, skip=skip, limit=limit)
        elif current_user_context.school:
            return crud_course.get_courses_by_school(db, school_id=current_user_context.school.id, skip=skip, limit=limit)
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view courses.")

    def get_user_courses(self, db: Session, current_user_context: UserContext) -> List[Course]:
        return crud_course.get_courses_by_user_id(db, user_id=current_user_context.user.id)

    def get_courses_by_school_id(self, db: Session, school_id: int, current_user_context: UserContext, skip: int = 0, limit: int = 100) -> List[Course]:
        if current_user_context.role.name == RoleEnum.SUPER_ADMIN:
            return crud_course.get_courses_by_school(db, school_id=school_id, skip=skip, limit=limit)
        elif current_user_context.school and current_user_context.school.id == school_id:
            return crud_course.get_courses_by_school(db, school_id=school_id, skip=skip, limit=limit)
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view courses for this school.")

course_service = CourseService()
