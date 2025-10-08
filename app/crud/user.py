from typing import Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime
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

    def get_users_by_school_and_role_count(self, db: Session, *, school_id: int, role_id: int, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> int:
        query = db.query(User)\
            .join(user_school_association, User.id == user_school_association.c.user_id)\
            .filter(
                user_school_association.c.school_id == school_id,
                user_school_association.c.role_id == role_id
            )
        if start_date:
            query = query.filter(User.created_at >= start_date)
        if end_date:
            query = query.filter(User.created_at <= end_date)
        return query.count()

    def get_users_by_school_count(self, db: Session, *, school_id: int, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> int:
        query = db.query(User)\
            .join(user_school_association, User.id == user_school_association.c.user_id)\
            .filter(user_school_association.c.school_id == school_id)
        if start_date:
            query = query.filter(User.created_at >= start_date)
        if end_date:
            query = query.filter(User.created_at <= end_date)
        return query.count()

    def get_non_student_users_by_school_count(self, db: Session, *, school_id: int, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> int:
        student_role = db.query(Role).filter(Role.name == "student").first()
        if not student_role:
            return 0

        query = db.query(User)\
            .join(user_school_association, User.id == user_school_association.c.user_id)\
            .filter(
                user_school_association.c.school_id == school_id,
                user_school_association.c.role_id != student_role.id
            )

        if start_date:
            query = query.filter(User.created_at >= start_date)
        if end_date:
            query = query.filter(User.created_at <= end_date)

        return query.count()

    def get_leaderboard_data_for_school(
        self, db: Session, school_id: int, skip: int = 0, limit: int = 100, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> List[dict]:
        student_role = db.query(Role).filter(Role.name == "student").first()
        if not student_role:
            return []

        lessons_completed_sq_query = (
            db.query(
                CourseEnrollment.user_id,
                func.count(LessonProgress.id).label("lessons_completed_count")
            )
            .join(CourseEnrollment, LessonProgress.enrollment_id == CourseEnrollment.id)
            .filter(LessonProgress.is_completed == True)
        )
        if start_date:
            lessons_completed_sq_query = lessons_completed_sq_query.filter(LessonProgress.created_at >= start_date)
        if end_date:
            lessons_completed_sq_query = lessons_completed_sq_query.filter(LessonProgress.created_at <= end_date)
        lessons_completed_sq = lessons_completed_sq_query.group_by(CourseEnrollment.user_id).subquery()

        accumulated_exam_score_sq_query = (
            db.query(
                ExamAttempt.user_id,
                func.sum(ExamAttempt.score).label("accumulated_exam_score_sum")
            )
            .filter(ExamAttempt.status == "completed")
        )
        if start_date:
            accumulated_exam_score_sq_query = accumulated_exam_score_sq_query.filter(ExamAttempt.created_at >= start_date)
        if end_date:
            accumulated_exam_score_sq_query = accumulated_exam_score_sq_query.filter(ExamAttempt.created_at <= end_date)
        accumulated_exam_score_sq = accumulated_exam_score_sq_query.group_by(ExamAttempt.user_id).subquery()

        total_rewards_sq_query = (
            db.query(
                CourseEnrollment.user_id,
                func.sum(CourseReward.points).label("total_rewards_sum")
            )
            .join(CourseEnrollment, CourseReward.enrollment_id == CourseEnrollment.id)
        )
        if start_date:
            total_rewards_sq_query = total_rewards_sq_query.filter(CourseReward.awarded_at >= start_date)
        if end_date:
            total_rewards_sq_query = total_rewards_sq_query.filter(CourseReward.awarded_at <= end_date)
        total_rewards_sq = total_rewards_sq_query.group_by(CourseEnrollment.user_id).subquery()

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

    def get_top_performer_by_exam_score(self, db: Session, school_id: int, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> Optional[dict]:
        student_role = db.query(Role).filter(Role.name == "student").first()
        if not student_role:
            return None

        query = (
            db.query(
                User.id.label("user_id"),
                User.full_name.label("full_name"),
                User.email.label("email"),
                func.sum(ExamAttempt.score).label("accumulated_exam_score")
            )
            .join(user_school_association, User.id == user_school_association.c.user_id)
            .filter(
                user_school_association.c.school_id == school_id,
                user_school_association.c.role_id == student_role.id
            )
            .join(ExamAttempt, User.id == ExamAttempt.user_id)
            .filter(ExamAttempt.status == "completed")
        )
        if start_date:
            query = query.filter(ExamAttempt.created_at >= start_date)
        if end_date:
            query = query.filter(ExamAttempt.created_at <= end_date)
        query = query.group_by(User.id, User.full_name, User.email)\
            .order_by(desc("accumulated_exam_score"))\
            .first()
        return query._asdict() if query else None

    def get_most_active_user_by_lessons_completed(self, db: Session, school_id: int, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> Optional[dict]:
        student_role = db.query(Role).filter(Role.name == "student").first()
        if not student_role:
            return None

        query = (
            db.query(
                User.id.label("user_id"),
                User.full_name.label("full_name"),
                User.email.label("email"),
                func.count(LessonProgress.id).label("lessons_completed")
            )
            .join(user_school_association, User.id == user_school_association.c.user_id)
            .filter(
                user_school_association.c.school_id == school_id,
                user_school_association.c.role_id == student_role.id
            )
            .join(CourseEnrollment, User.id == CourseEnrollment.user_id)
            .join(LessonProgress, CourseEnrollment.id == LessonProgress.enrollment_id)
            .filter(LessonProgress.is_completed == True)
        )
        if start_date:
            query = query.filter(LessonProgress.created_at >= start_date)
        if end_date:
            query = query.filter(LessonProgress.created_at <= end_date)
        query = query.group_by(User.id, User.full_name, User.email)\
            .order_by(desc("lessons_completed"))\
            .first()
        return query._asdict() if query else None

    def get_all_students_count(self, db: Session, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> int:
        student_role = db.query(Role).filter(Role.name == "student").first()
        if not student_role:
            return 0

        query = db.query(User)\
            .join(user_school_association, User.id == user_school_association.c.user_id)\
            .filter(user_school_association.c.role_id == student_role.id)
        if start_date:
            query = query.filter(User.created_at >= start_date)
        if end_date:
            query = query.filter(User.created_at <= end_date)
        return query.count()

    def get_all_teachers_count(self, db: Session, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> int:
        teacher_role = db.query(Role).filter(Role.name == "teacher").first()
        if not teacher_role:
            return 0

        query = db.query(User)\
            .join(user_school_association, User.id == user_school_association.c.user_id)\
            .filter(user_school_association.c.role_id == teacher_role.id)
        if start_date:
            query = query.filter(User.created_at >= start_date)
        if end_date:
            query = query.filter(User.created_at <= end_date)
        return query.count()

user = CRUDUser(User)