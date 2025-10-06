from typing import Optional, List
from sqlalchemy.orm import Session
from datetime import datetime
from sqlalchemy import func
from app.crud.base import CRUDBase
from app.models.school import School
from app.schemas.school import SchoolCreate, SchoolUpdate
from app.models.user import User
from app.models.role import Role
from app.models.user_school_association import user_school_association
from app.core.constants import RoleEnum

class CRUDSchool(CRUDBase[School, SchoolCreate, SchoolUpdate]):

    def get_by_name(self, db: Session, *, name: str) -> Optional[School]:
        return db.query(School).filter(School.name == name).first()

    def get_all_schools_count(self, db: Session, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> int:
        query = db.query(School)
        if start_date:
            query = query.filter(School.created_at >= start_date)
        if end_date:
            query = query.filter(School.created_at <= end_date)
        return query.count()

    def get_admin_school_data(self, db: Session, skip: int = 0, limit: int = 100) -> List[dict]:
        # Subquery for teacher count per school
        teachers_count_sq = (
            db.query(
                user_school_association.c.school_id,
                func.count(user_school_association.c.user_id).label("total_teachers")
            )
            .join(Role, user_school_association.c.role_id == Role.id)
            .filter(Role.name == RoleEnum.TEACHER)
            .group_by(user_school_association.c.school_id)
            .subquery()
        )

        # Subquery for student count per school
        students_count_sq = (
            db.query(
                user_school_association.c.school_id,
                func.count(user_school_association.c.user_id).label("total_students")
            )
            .join(Role, user_school_association.c.role_id == Role.id)
            .filter(Role.name == RoleEnum.STUDENT)
            .group_by(user_school_association.c.school_id)
            .subquery()
        )

        # Subquery to find the creator (first SCHOOL_ADMIN) for each school
        creator_sq = (
            db.query(
                user_school_association.c.school_id,
                User.full_name.label("creator_name"),
                User.email.label("creator_email")
            )
            .join(User, user_school_association.c.user_id == User.id)
            .join(Role, user_school_association.c.role_id == Role.id)
            .filter(Role.name == RoleEnum.SCHOOL_ADMIN)
            .group_by(user_school_association.c.school_id, User.full_name, User.email)
            .order_by(user_school_association.c.school_id, User.id) # Order to pick the "first" admin
            .distinct(user_school_association.c.school_id)
            .subquery()
        )


        query = (
            db.query(
                School.id.label("school_id"),
                School.name.label("school_name"),
                func.coalesce(creator_sq.c.creator_name, "N/A").label("creator_name"),
                func.coalesce(creator_sq.c.creator_email, "N/A").label("creator_email"),
                func.coalesce(teachers_count_sq.c.total_teachers, 0).label("total_teachers"),
                func.coalesce(students_count_sq.c.total_students, 0).label("total_students"),
                School.is_active.label("is_active")
            )
            .outerjoin(teachers_count_sq, School.id == teachers_count_sq.c.school_id)
            .outerjoin(students_count_sq, School.id == students_count_sq.c.school_id)
            .outerjoin(creator_sq, School.id == creator_sq.c.school_id)
            .offset(skip)
            .limit(limit)
        )

        return query.all()

school = CRUDSchool(School)
