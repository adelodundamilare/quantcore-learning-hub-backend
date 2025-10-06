from typing import Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app.crud.base import CRUDBase
from app.models.course_enrollment import CourseEnrollment
from app.models.user import User
from app.models.school import School
from app.models.role import Role
from app.models.user_school_association import user_school_association
from app.models.lesson_progress import LessonProgress
from app.models.exam_attempt import ExamAttempt
from app.models.course_reward import CourseReward

from app.schemas.user import UserCreate, UserUpdate

class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    def get_by_email(self, db: Session, *, email: str) -> User | None:
        return db.query(User).filter(User.email == email).first()

    def get_user_contexts(self, db: Session, *, user_id: int) -> List[dict]:
        results = (
            db.query(School, Role)
            .join(user_school_association, School.id == user_school_association.c.school_id)
            .join(Role, Role.id == user_school_association.c.role_id)
            .filter(user_school_association.c.user_id == user_id)
            .all()
        )
        return [{"school": school, "role": role} for school, role in results]

    def get_association_by_user_school_role(self, db: Session, *, user_id: int, school_id: int, role_id: int) -> Any | None:
        return db.query(user_school_association).filter(
            user_school_association.c.user_id == user_id,
            user_school_association.c.school_id == school_id,
            user_school_association.c.role_id == role_id
        ).first()

    def get_users_by_school_and_role(self, db: Session, *, school_id: int, role_id: int, skip: int = 0, limit: int = 100) -> List[User]:
        return (
            db.query(User)
            .join(user_school_association, User.id == user_school_association.c.user_id)
            .filter(
                user_school_association.c.school_id == school_id,
                user_school_association.c.role_id == role_id
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    def add_user_to_school(self, db: Session, *, user: User, school: School, role: Role) -> None:
        stmt = user_school_association.insert().values(
            user_id=user.id,
            school_id=school.id,
            role_id=role.id
        )
        db.execute(stmt)

    def get_users_by_school_and_role_count(self, db: Session, *, school_id: int, role_id: int) -> int:
        return (
            db.query(User)
            .join(user_school_association, User.id == user_school_association.c.user_id)
            .filter(
                user_school_association.c.school_id == school_id,
                user_school_association.c.role_id == role_id
            )
            .count()
        )

    def get_users_by_school_count(self, db: Session, *, school_id: int) -> int:
        return (
            db.query(User)
            .join(user_school_association, User.id == user_school_association.c.user_id)
            .filter(user_school_association.c.school_id == school_id)
            .count()
        )

    def get_leaderboard_data_for_school(
        self, db: Session, school_id: int, skip: int = 0, limit: int = 100
    ) -> List[dict]:
        student_role = db.query(Role).filter(Role.name == "student").first()
        if not student_role:
            return []

        lessons_completed_sq = (
            db.query(
                CourseEnrollment.user_id,
                func.count(LessonProgress.id).label("lessons_completed_count")
            )
            .join(CourseEnrollment, LessonProgress.enrollment_id == CourseEnrollment.id)
            .filter(LessonProgress.is_completed == True)
            .group_by(CourseEnrollment.user_id)
            .subquery()
        )

        accumulated_exam_score_sq = (
            db.query(
                ExamAttempt.user_id,
                func.sum(ExamAttempt.score).label("accumulated_exam_score_sum")
            )
            .filter(ExamAttempt.status == "completed")
            .group_by(ExamAttempt.user_id)
            .subquery()
        )

        total_rewards_sq = (
            db.query(
                CourseEnrollment.user_id,
                func.sum(CourseReward.points).label("total_rewards_sum")
            )
            .join(CourseEnrollment, CourseReward.enrollment_id == CourseEnrollment.id)
            .group_by(CourseEnrollment.user_id)
            .subquery()
        )

        query = (
            db.query(
                User.id.label("student_id"),
                User.full_name.label("student_full_name"),
                User.email.label("student_email"),
                func.coalesce(lessons_completed_sq.c.lessons_completed_count, 0).label("lessons_completed"),
                func.coalesce(accumulated_exam_score_sq.c.accumulated_exam_score_sum, 0.0).label("accumulated_exam_score"),
                func.coalesce(total_rewards_sq.c.total_rewards_sum, 0).label("total_rewards")
            )
            .join(user_school_association, User.id == user_school_association.c.user_id)
            .filter(
                user_school_association.c.school_id == school_id,
                user_school_association.c.role_id == student_role.id
            )
            .outerjoin(lessons_completed_sq, User.id == lessons_completed_sq.c.user_id)
            .outerjoin(accumulated_exam_score_sq, User.id == accumulated_exam_score_sq.c.user_id)
            .outerjoin(total_rewards_sq, User.id == total_rewards_sq.c.user_id)
            .order_by(desc("total_rewards"))
            .offset(skip)
            .limit(limit)
        )

        return query.all()

user = CRUDUser(User)