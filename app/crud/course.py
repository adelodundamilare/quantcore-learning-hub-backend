from sqlalchemy.orm import Session
from typing import List, Type

from app.crud.base import CRUDBase
from app.models.course import Course, course_teachers_association, course_students_association
from app.models.user import User
from app.schemas.course import CourseCreate, CourseUpdate

class CRUDCourse(CRUDBase[Course, CourseCreate, CourseUpdate]):
    """CRUD operations for Courses."""

    def add_teacher_to_course(self, db: Session, *, course: Course, user: User) -> None:
        course.teachers.append(user)
        db.add(course)

    def remove_teacher_from_course(self, db: Session, *, course: Course, user: User) -> None:
        course.teachers.remove(user)
        db.add(course)

    def enroll_student_in_course(self, db: Session, *, course: Course, user: User) -> None:
        course.students.append(user)
        db.add(course)

    def unenroll_student_from_course(self, db: Session, *, course: Course, user: User) -> None:
        course.students.remove(user)
        db.add(course)

    def get_courses_by_user_id(self, db: Session, user_id: int) -> List[Course]:
        # Get courses where user is a teacher
        teacher_courses = (
            db.query(Course)
            .join(course_teachers_association)
            .filter(course_teachers_association.c.user_id == user_id)
            .all()
        )
        # Get courses where user is a student
        student_courses = (
            db.query(Course)
            .join(course_students_association)
            .filter(course_students_association.c.user_id == user_id)
            .all()
        )
        # Combine and return unique courses
        return list(set(teacher_courses + student_courses))

course = CRUDCourse(Course)
