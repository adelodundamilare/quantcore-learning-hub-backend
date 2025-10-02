from sqlalchemy.orm import Session, selectinload
from typing import List

from app.crud.base import CRUDBase
from app.models.course_reward import CourseReward
from app.schemas.reward_rating import CourseRewardCreate, CourseRewardUpdate


class CRUDCourseReward(CRUDBase[CourseReward, CourseRewardCreate, CourseRewardUpdate]):

    def _query_with_relationships(self, db: Session):
        return db.query(CourseReward).options(
            selectinload(CourseReward.enrollment)
        )

    def _query_active(self, db: Session):
        return self._query_with_relationships(db).filter(CourseReward.deleted_at.is_(None))

    def get(self, db: Session, id: int):
        return self._query_active(db).filter(CourseReward.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100) -> List[CourseReward]:
        return (
            self._query_active(db)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_enrollment(self, db: Session, enrollment_id: int) -> List[CourseReward]:
        return (
            self._query_active(db)
            .filter(CourseReward.enrollment_id == enrollment_id)
            .order_by(CourseReward.awarded_at.desc())
            .all()
        )

    def get_by_user(self, db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[CourseReward]:
        return (
            self._query_active(db)
            .join(CourseReward.enrollment)
            .filter(CourseReward.enrollment.has(user_id=user_id))
            .order_by(CourseReward.awarded_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_total_points_by_user(self, db: Session, user_id: int) -> int:
        result = (
            self._query_active(db)
            .join(CourseReward.enrollment)
            .filter(CourseReward.enrollment.has(user_id=user_id))
            .with_entities(db.func.sum(CourseReward.points))
            .scalar()
        )
        return result or 0


course_reward = CRUDCourseReward(CourseReward)