from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func
from typing import List, Optional, Dict

from app.crud.base import CRUDBase
from app.models.course_rating import CourseRating
from app.schemas.reward_rating import CourseRatingCreate, CourseRatingUpdate


class CRUDCourseRating(CRUDBase[CourseRating, CourseRatingCreate, CourseRatingUpdate]):

    def _query_with_relationships(self, db: Session):
        return db.query(CourseRating).options(
            selectinload(CourseRating.user),
            selectinload(CourseRating.course)
        )

    def _query_active(self, db: Session):
        return self._query_with_relationships(db).filter(CourseRating.deleted_at.is_(None))

    def get(self, db: Session, id: int):
        return self._query_active(db).filter(CourseRating.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100) -> List[CourseRating]:
        return (
            self._query_active(db)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_user_and_course(self, db: Session, user_id: int, course_id: int) -> Optional[CourseRating]:
        return (
            self._query_active(db)
            .filter(CourseRating.user_id == user_id)
            .filter(CourseRating.course_id == course_id)
            .first()
        )

    def get_by_course(self, db: Session, course_id: int, skip: int = 0, limit: int = 100) -> List[CourseRating]:
        return (
            self._query_active(db)
            .filter(CourseRating.course_id == course_id)
            .order_by(CourseRating.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_user(self, db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[CourseRating]:
        return (
            self._query_active(db)
            .filter(CourseRating.user_id == user_id)
            .order_by(CourseRating.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_average_rating(self, db: Session, course_id: int) -> float:
        result = (
            self._query_active(db)
            .filter(CourseRating.course_id == course_id)
            .with_entities(func.avg(CourseRating.rating))
            .scalar()
        )
        return round(float(result), 2) if result else 0.0

    def get_rating_count(self, db: Session, course_id: int) -> int:
        return (
            self._query_active(db)
            .filter(CourseRating.course_id == course_id)
            .count()
        )

    def get_rating_distribution(self, db: Session, course_id: int) -> Dict[int, int]:
        results = (
            self._query_active(db)
            .filter(CourseRating.course_id == course_id)
            .with_entities(
                func.floor(CourseRating.rating).label('rating_group'),
                func.count().label('count')
            )
            .group_by('rating_group')
            .all()
        )

        distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for rating_group, count in results:
            distribution[int(rating_group)] = count

        return distribution


course_rating = CRUDCourseRating(CourseRating)