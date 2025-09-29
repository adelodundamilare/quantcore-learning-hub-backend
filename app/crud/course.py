from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List

from app.crud.base import CRUDBase
from app.models.course import Course, course_teachers_association, course_students_association
from app.models.user import User
from app.schemas.course import CourseCreate, CourseUpdate

class CRUDCourse(CRUDBase[Course, CourseCreate, CourseUpdate]):
    """CRUD operations for Courses."""

    def add_teacher_to_course(self, db: Session, *, course: Course, user: User, commit: bool = True) -> None:
        if user not in course.teachers:
            course.teachers.append(user)
            db.add(course)
            if commit:
                db.commit()

    def remove_teacher_from_course(self, db: Session, *, course: Course, user: User, commit: bool = True) -> None:
        if user in course.teachers:
            course.teachers.remove(user)
            db.add(course)
            if commit:
                db.commit()

    def enroll_student_in_course(self, db: Session, *, course: Course, user: User, commit: bool = True) -> None:
        if user not in course.students:
            course.students.append(user)
            db.add(course)
            if commit:
                db.commit()

    def unenroll_student_from_course(self, db: Session, *, course: Course, user: User) -> None:
        if user in course.students:
            course.students.remove(user)
            db.add(course)

    def get_courses_by_user_id(self, db: Session, user_id: int) -> List[Course]:
        """Get all courses where user is either a teacher or student."""
        return (
            db.query(Course)
            .join(course_teachers_association, Course.id == course_teachers_association.c.course_id, isouter=True)
            .join(course_students_association, Course.id == course_students_association.c.course_id, isouter=True)
            .filter(
                or_(
                    course_teachers_association.c.user_id == user_id,
                    course_students_association.c.user_id == user_id
                )
            )
            .distinct()
            .all()
        )

    def get_teacher_courses(self, db: Session, user_id: int) -> List[Course]:
        """Get courses where user is a teacher."""
        return (
            db.query(Course)
            .join(course_teachers_association)
            .filter(course_teachers_association.c.user_id == user_id)
            .all()
        )

    def get_student_courses(self, db: Session, user_id: int) -> List[Course]:
        """Get courses where user is a student."""
        return (
            db.query(Course)
            .join(course_students_association)
            .filter(course_students_association.c.user_id == user_id)
            .all()
        )

    def get_courses_by_school(self, db: Session, school_id: int, skip: int = 0, limit: int = 100) -> List[Course]:
        """Get courses by school with pagination."""
        return (
            db.query(Course)
            .filter(Course.school_id == school_id)
            .filter(Course.deleted_at.is_(None))  # Exclude soft-deleted courses
            .offset(skip)
            .limit(limit)
            .all()
        )

    def is_user_enrolled(self, db: Session, *, course_id: int, user_id: int) -> bool:
        """Check if user is enrolled in course (as student or teacher)."""
        course = db.get(Course, course_id)
        if not course:
            return False

        user = db.get(User, user_id)
        if not user:
            return False

        return user in course.students or user in course.teachers

    def get_active_courses(self, db: Session, skip: int = 0, limit: int = 100) -> List[Course]:
        """Get active, non-deleted courses."""
        return (
            db.query(Course)
            .filter(Course.is_active == True)
            .filter(Course.deleted_at.is_(None))
            .offset(skip)
            .limit(limit)
            .all()
        )

course = CRUDCourse(Course)