from sqlalchemy.orm import Session, selectinload
from typing import List, Optional

from app.crud.base import CRUDBase
from app.models.lesson_progress import LessonProgress
from app.schemas.lesson_progress import LessonProgressCreate, LessonProgressUpdate

class CRUDLessonProgress(CRUDBase[LessonProgress, LessonProgressCreate, LessonProgressUpdate]):

    def _query_with_relationships(self, db: Session):
        return db.query(LessonProgress).options(
            selectinload(LessonProgress.enrollment),
            selectinload(LessonProgress.lesson)
        )

    def _query_active(self, db: Session):
        return self._query_with_relationships(db).filter(LessonProgress.deleted_at.is_(None))

    def get(self, db: Session, id: int):
        return self._query_active(db).filter(LessonProgress.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100) -> List[LessonProgress]:
        return (
            self._query_active(db)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_enrollment_and_lesson(self, db: Session, enrollment_id: int, lesson_id: int) -> Optional[LessonProgress]:
        return (
            self._query_active(db)
            .filter(LessonProgress.enrollment_id == enrollment_id)
            .filter(LessonProgress.lesson_id == lesson_id)
            .first()
        )

    def get_all_by_enrollment(self, db: Session, enrollment_id: int) -> List[LessonProgress]:
        return (
            self._query_active(db)
            .filter(LessonProgress.enrollment_id == enrollment_id)
            .order_by(LessonProgress.started_at)
            .all()
        )

    def get_completed_lesson_ids(self, db: Session, enrollment_id: int) -> List[int]:
        results = (
            self._query_active(db)
            .filter(LessonProgress.enrollment_id == enrollment_id)
            .filter(LessonProgress.is_completed == True)
            .all()
        )
        return [lp.lesson_id for lp in results]

    def get_by_lesson(self, db: Session, lesson_id: int, skip: int = 0, limit: int = 100) -> List[LessonProgress]:
        return (
            self._query_active(db)
            .filter(LessonProgress.lesson_id == lesson_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_completed_by_enrollment(self, db: Session, enrollment_id: int) -> List[LessonProgress]:
        return (
            self._query_active(db)
            .filter(LessonProgress.enrollment_id == enrollment_id)
            .filter(LessonProgress.is_completed == True)
            .all()
        )


lesson_progress = CRUDLessonProgress(LessonProgress)