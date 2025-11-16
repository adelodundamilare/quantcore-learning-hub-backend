from sqlalchemy.orm import Session, selectinload
from typing import List, Optional
from datetime import datetime

from app.crud.base import CRUDBase
from app.models.course_enrollment import CourseEnrollment, EnrollmentStatusEnum
from app.models.course import Course
from app.crud.course_reward import course_reward
from app.models.curriculum import Curriculum
from app.models.user import User
from app.schemas.course_enrollment import CourseEnrollmentCreate, CourseEnrollmentUpdate

class CRUDCourseEnrollment(CRUDBase[CourseEnrollment, CourseEnrollmentCreate, CourseEnrollmentUpdate]):

    def _query_with_relationships(self, db: Session):
        return db.query(CourseEnrollment).options(
            selectinload(CourseEnrollment.user),
            selectinload(CourseEnrollment.course).selectinload(Course.curriculums).selectinload(Curriculum.lessons),
            selectinload(CourseEnrollment.lesson_progress)
        )

    def _query_active(self, db: Session):
        return self._query_with_relationships(db).filter(CourseEnrollment.deleted_at.is_(None))

    def get(self, db: Session, id: int):
        return self._query_active(db).filter(CourseEnrollment.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100) -> List[CourseEnrollment]:
        return (
            self._query_active(db)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_user_and_course(self, db: Session, user_id: int, course_id: int) -> Optional[CourseEnrollment]:
        return (
            self._query_active(db)
            .filter(CourseEnrollment.user_id == user_id)
            .filter(CourseEnrollment.course_id == course_id)
            .first()
        )

    def get_by_user(self, db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[CourseEnrollment]:
        return (
            self._query_active(db)
            .filter(CourseEnrollment.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_course(self, db: Session, course_id: int, skip: int = 0, limit: int = 100) -> List[CourseEnrollment]:
        return (
            self._query_active(db)
            .filter(CourseEnrollment.course_id == course_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_in_progress_by_user(self, db: Session, user_id: int) -> List[CourseEnrollment]:
        return (
            self._query_active(db)
            .filter(CourseEnrollment.user_id == user_id)
            .filter(CourseEnrollment.status == "in_progress")
            .all()
        )

    def get_completed_by_user(self, db: Session, user_id: int) -> List[CourseEnrollment]:
        return (
            self._query_active(db)
            .filter(CourseEnrollment.user_id == user_id)
            .filter(CourseEnrollment.status == "completed")
            .all()
        )

    def get_student_count_for_course(self, db: Session, course_id: int) -> int:
        return (
            self._query_active(db)
            .filter(CourseEnrollment.course_id == course_id)
            .count()
        )

    def get_completed_unrewarded_by_school(self, db: Session, school_id: int):

        enrollments = db.query(CourseEnrollment).join(
            Course, Course.id == CourseEnrollment.course_id
        ).join(
            User, User.id == CourseEnrollment.user_id
        ).filter(
            Course.school_id == school_id,
            CourseEnrollment.status == EnrollmentStatusEnum.COMPLETED,
            ~db.query(course_reward.model).filter(
                course_reward.model.enrollment_id == CourseEnrollment.id
            ).exists()
        ).all()

        result = []
        for enrollment in enrollments:
            result.append({
                "id": enrollment.id,
                "user_id": enrollment.user_id,
                "course_id": enrollment.course_id,
                "user_name": enrollment.user.full_name,
                "course_name": enrollment.course.title,
                "completed_at": enrollment.completed_at,
                "has_reward": False
            })

        return result

    def update_status(self, db: Session, enrollment_id: int, status: EnrollmentStatusEnum):
        enrollment = self.get(db, id=enrollment_id)
        if enrollment:
            enrollment.status = status
            if status == EnrollmentStatusEnum.COMPLETED:
                enrollment.completed_at = datetime.now()
            db.commit()
            db.refresh(enrollment)
        return enrollment

course_enrollment = CRUDCourseEnrollment(CourseEnrollment)
