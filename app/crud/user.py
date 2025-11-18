from typing import Any, Optional, List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc
from datetime import datetime, timezone
from app.core.constants import CourseLevelEnum
from app.crud.base import CRUDBase
from app.models.course_enrollment import CourseEnrollment
from app.models.user import User
from app.models.school import School
from app.models.role import Role
from app.models.user_school_association import user_school_association
from app.models.lesson_progress import LessonProgress
from app.models.exam_attempt import ExamAttempt
from app.models.course_reward import CourseReward
from app.models.user_school_association import UserSchoolAssociation


from app.schemas.user import UserCreate, UserUpdate

class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    def get(self, db: Session, id: Any) -> Optional[User]:
        query = db.query(self.model).options(joinedload(self.model.stripe_customer)).filter(self.model.id == id)
        if hasattr(self.model, 'deleted_at'):
            query = query.filter(self.model.deleted_at == None)
        return query.first()

    def get_by_email(self, db: Session, *, email: str) -> User | None:
        return db.query(User).filter(User.email == email, User.deleted_at == None).first()

    def get_by_email_with_soft_deleted(self, db: Session, *, email: str) -> User | None:
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

    def get_association_by_user_school_role(self, db: Session, *, user_id: int, school_id: int, role_id: int) -> tuple[Role, Any] | None:
        result = db.query(Role, user_school_association).join(
            user_school_association, user_school_association.c.role_id == Role.id
        ).filter(
            user_school_association.c.user_id == user_id,
            user_school_association.c.school_id == school_id,
            user_school_association.c.role_id == role_id
        ).first()
        return result

    def get_association_by_user_and_school(self, db: Session, *, user_id: int, school_id: int) -> tuple[Role, CourseLevelEnum] | None:
        result = db.query(Role, UserSchoolAssociation.level).join(
            UserSchoolAssociation, UserSchoolAssociation.role_id == Role.id
        ).filter(
            UserSchoolAssociation.user_id == user_id,
            UserSchoolAssociation.school_id == school_id,
            UserSchoolAssociation.deleted_at == None
        ).first()
        return result

    def get_users_by_school_and_role(self, db: Session, *, school_id: int, role_id: int, skip: int = 0, limit: int = 100) -> List[User]:
        return (
            db.query(User)
            .join(user_school_association, User.id == user_school_association.c.user_id)
            .filter(
                user_school_association.c.school_id == school_id,
                user_school_association.c.role_id == role_id,
                user_school_association.c.deleted_at == None
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_users_by_role_names(self, db: Session, *, role_names: List[str], skip: int = 0, limit: int = 100) -> List[tuple[User, Role]]:
        return (
            db.query(User, Role)
            .join(user_school_association, User.id == user_school_association.c.user_id)
            .join(Role, user_school_association.c.role_id == Role.id)
            .filter(Role.name.in_(role_names))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_non_student_users_by_school(self, db: Session, *, school_id: int, skip: int = 0, limit: int = 100) -> List[User]:
        student_role = db.query(Role).filter(Role.name == "student").first()
        if not student_role:
            return []

        return (
            db.query(User)
            .join(user_school_association, User.id == user_school_association.c.user_id)
            .filter(
                user_school_association.c.school_id == school_id,
                user_school_association.c.role_id != student_role.id,
                user_school_association.c.deleted_at == None
            )
            .offset(skip)
            .limit(limit)
            .all()
        )

    def add_user_to_school(self, db: Session, *, user: User, school: School, role: Role, level: Optional[CourseLevelEnum] = None) -> None:
        stmt = user_school_association.insert().values(
            user_id=user.id,
            school_id=school.id,
            role_id=role.id,
            level=level
        )
        db.execute(stmt)

    def update_association(self, db: Session, *, user_id: int, school_id: int, role_id: Optional[int] = None, level: Optional[CourseLevelEnum] = None) -> None:
        values = {}
        if role_id is not None:
            values['role_id'] = role_id
        if level is not None:
            values['level'] = level
        if values:
            stmt = user_school_association.update().\
                where(user_school_association.c.user_id == user_id).\
                where(user_school_association.c.school_id == school_id).\
                values(**values)
            db.execute(stmt)

    def get_users_by_school_and_role_count(self, db: Session, *, school_id: int, role_id: int, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> int:
        query = db.query(User)\
            .join(user_school_association, User.id == user_school_association.c.user_id)\
            .filter(
                user_school_association.c.school_id == school_id,
                user_school_association.c.role_id == role_id,
                User.deleted_at == None
            )
        if start_date:
            query = query.filter(User.created_at >= start_date)
        if end_date:
            query = query.filter(User.created_at <= end_date)
        return query.count()

    def get_users_by_school_count(self, db: Session, *, school_id: int, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> int:
        query = db.query(User)\
            .join(user_school_association, User.id == user_school_association.c.user_id)\
            .filter(user_school_association.c.school_id == school_id, User.deleted_at == None)
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
                user_school_association.c.role_id != student_role.id,
                User.deleted_at == None
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
                user_school_association.c.role_id == student_role.id,
                User.deleted_at == None
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
                user_school_association.c.role_id == student_role.id,
                User.deleted_at == None
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
                user_school_association.c.role_id == student_role.id,
                User.deleted_at == None
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
            .filter(user_school_association.c.role_id == student_role.id, User.deleted_at == None)
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
            .filter(user_school_association.c.role_id == teacher_role.id, User.deleted_at == None)
        if start_date:
            query = query.filter(User.created_at >= start_date)
        if end_date:
            query = query.filter(User.created_at <= end_date)
        return query.count()

    def get_school_admin_count(self, db: Session, *, school_id: int) -> int:
        """Get the count of active school administrators for a school."""
        school_admin_role = db.query(Role).filter(Role.name == "school_admin").first()
        if not school_admin_role:
            return 0

        return db.query(user_school_association).filter(
            user_school_association.c.school_id == school_id,
            user_school_association.c.role_id == school_admin_role.id,
            user_school_association.c.deleted_at == None
        ).count()

    def update_user_password(self, db: Session, *, user: User, hashed_password: str) -> User:
        """Update a user's password hash."""
        user.hashed_password = hashed_password
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def soft_delete_user_association(self, db: Session, *, user_id: int, school_id: int) -> None:
        """Soft delete a user-school association."""
        stmt = user_school_association.update().\
        where(user_school_association.c.user_id == user_id).\
        where(user_school_association.c.school_id == school_id).\
        where(user_school_association.c.deleted_at == None).\
        values(deleted_at=datetime.now(timezone.utc))

        db.execute(stmt)
        db.commit()

    def update_user_active_status(self, db: Session, *, user: User, is_active: bool) -> User:
        """Update a user's active status."""
        user.is_active = is_active
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def get_student_school_associations(self, db: Session, student_id: int) -> List[Any]:
        """Get all school associations for a student."""
        from app.models.user import user_school_association
        student_role = db.query(Role).filter(Role.name == "student").first()
        if not student_role:
            return []

        return db.query(user_school_association).filter(
            user_school_association.c.user_id == student_id,
            user_school_association.c.role_id == student_role.id
        ).all()

    def bulk_delete_related_entities(self, db: Session, user_id: int) -> None:
        """Permanently delete all user-related entities (for admin deletion)"""
        db.query(ExamAttempt).filter(ExamAttempt.user_id == user_id).delete()
        db.query(CourseEnrollment).filter(CourseEnrollment.user_id == user_id).delete()
        db.query(user_school_association).filter(user_school_association.c.user_id == user_id).delete()


user = CRUDUser(User)
