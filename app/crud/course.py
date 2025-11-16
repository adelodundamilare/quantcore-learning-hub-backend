from sqlalchemy.orm import Session, selectinload
from sqlalchemy import or_
from typing import List, Optional
from datetime import datetime

from app.crud.base import CRUDBase
from app.models.course import Course, course_teachers_association, course_students_association
from app.models.course_enrollment import CourseEnrollment
from app.models.curriculum import Curriculum
from app.models.user import User
from app.schemas.course import CourseCreate, CourseUpdate


class CRUDCourse(CRUDBase[Course, CourseCreate, CourseUpdate]):

    def _query_with_relationships(self, db: Session):
        return db.query(Course).options(
            selectinload(Course.teachers),
            selectinload(Course.students),
            selectinload(Course.school),
            selectinload(Course.curriculums).selectinload(Curriculum.lessons),
            selectinload(Course.enrollments).selectinload(CourseEnrollment.lesson_progress)
        )

    def _query_active(self, db: Session):
        return self._query_with_relationships(db).filter(Course.deleted_at.is_(None))

    def get(self, db: Session, id: int):
        return self._query_active(db).filter(Course.id == id).first()

    def add_teacher_to_course(self, db: Session, *, course: Course, user: User) -> Course:
        if user not in course.teachers:
            course.teachers.append(user)
            db.add(course)
        return course

    def remove_teacher_from_course(self, db: Session, *, course: Course, user: User) -> Course:
        if user in course.teachers:
            course.teachers.remove(user)
            db.add(course)
        return course

    def enroll_student_in_course(self, db: Session, *, course: Course, user: User) -> Course:
        if user not in course.students:
            course.students.append(user)
            db.add(course)
        return course

    def unenroll_student_from_course(self, db: Session, *, course: Course, user: User) -> Course:
        if user in course.students:
            course.students.remove(user)
            db.add(course)
        return course

    def get_courses_by_user_id(self, db: Session, user_id: int) -> List[Course]:
        return (
            self._query_active(db)
            .join(course_teachers_association, Course.id == course_teachers_association.c.course_id, isouter=True)
            .join(course_students_association, Course.id == course_students_association.c.course_id, isouter=True)
            .join(User, or_(
                course_teachers_association.c.user_id == User.id,
                course_students_association.c.user_id == User.id
            ), isouter=True)
            .filter(
                or_(
                    course_teachers_association.c.user_id == user_id,
                    course_students_association.c.user_id == user_id
                )
            )
            .filter(User.deleted_at == None)
            .distinct()
            .all()
        )

    def get_teacher_courses(self, db: Session, user_id: int) -> List[Course]:
        return (
            self._query_active(db)
            .join(course_teachers_association)
            .join(User, course_teachers_association.c.user_id == User.id)
            .filter(course_teachers_association.c.user_id == user_id)
            .filter(User.deleted_at == None)
            .all()
        )

    def get_student_courses(self, db: Session, user_id: int) -> List[Course]:
        return (
            self._query_active(db)
            .join(course_students_association)
            .join(User, course_students_association.c.user_id == User.id)
            .filter(course_students_association.c.user_id == user_id)
            .filter(User.deleted_at == None)
            .all()
        )

    def get_courses_by_school(self, db: Session, school_id: int, skip: int = 0, limit: int = 100) -> List[Course]:
        return (
            self._query_active(db)
            .filter(Course.school_id == school_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100) -> List[Course]:
        return (
            self._query_active(db)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def is_user_enrolled(self, db: Session, *, course_id: int, user_id: int) -> bool:
        course = self.get(db, id=course_id)
        if not course:
            return False

        user = db.get(User, user_id)
        if not user:
            return False

        return user in course.students or user in course.teachers

    def get_active_courses(self, db: Session, skip: int = 0, limit: int = 100) -> List[Course]:
        return (
            self._query_active(db)
            .filter(Course.is_active == True)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_courses_by_school_count(self, db: Session, school_id: int, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> int:
        query = self._query_active(db).filter(Course.school_id == school_id)
        if start_date:
            query = query.filter(Course.created_at >= start_date)
        if end_date:
            query = query.filter(Course.created_at <= end_date)
        return query.count()

    def get_all_courses_count(self, db: Session, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> int:
        query = self._query_active(db)
        if start_date:
            query = query.filter(Course.created_at >= start_date)
        if end_date:
            query = query.filter(Course.created_at <= end_date)
        return query.count()


    def get_batch_with_relationships(self, db: Session, course_ids: List[int]) -> List[Course]:
        if not course_ids:
            return []

        return db.query(Course).options(
            selectinload(Course.enrollments),
            selectinload(Course.enrollments).selectinload(CourseEnrollment.lesson_progress),
            selectinload(Course.curriculums).selectinload(Curriculum.lessons)
        ).filter(Course.id.in_(course_ids)).filter(Course.deleted_at.is_(None)).all()


course = CRUDCourse(Course)
