from sqlalchemy.orm import Session, selectinload
from typing import List

from app.crud.base import CRUDBase
from app.models.exam_attempt import ExamAttempt
from app.schemas.exam_attempt import ExamAttemptCreate, ExamAttemptUpdate

class CRUDExamAttempt(CRUDBase[ExamAttempt, ExamAttemptCreate, ExamAttemptUpdate]):
    def _query_with_relationships(self, db: Session):
        return db.query(ExamAttempt).options(
            selectinload(ExamAttempt.exam),
            selectinload(ExamAttempt.user),
            selectinload(ExamAttempt.user_answers)
        )

    def _query_active(self, db: Session):
        return self._query_with_relationships(db).filter(ExamAttempt.deleted_at.is_(None))

    def get(self, db: Session, id: int):
        return self._query_active(db).filter(ExamAttempt.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100) -> List[ExamAttempt]:
        return (
            self._query_active(db)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_user_and_exam(self, db: Session, user_id: int, exam_id: int) -> List[ExamAttempt]:
        return (
            self._query_active(db)
            .filter(ExamAttempt.user_id == user_id)
            .filter(ExamAttempt.exam_id == exam_id)
            .order_by(ExamAttempt.start_time.desc())
            .all()
        )

    def get_all_by_user(self, db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[ExamAttempt]:
        return (
            self._query_active(db)
            .filter(ExamAttempt.user_id == user_id)
            .order_by(ExamAttempt.start_time.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_all_by_exam(self, db: Session, exam_id: int, skip: int = 0, limit: int = 100) -> List[ExamAttempt]:
        return (
            self._query_active(db)
            .filter(ExamAttempt.exam_id == exam_id)
            .order_by(ExamAttempt.start_time.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_in_progress_attempts(self, db: Session, user_id: int) -> List[ExamAttempt]:
        return (
            self._query_active(db)
            .filter(ExamAttempt.user_id == user_id)
            .filter(ExamAttempt.status == "in_progress")
            .order_by(ExamAttempt.start_time.desc())
            .all()
        )


exam_attempt = CRUDExamAttempt(ExamAttempt)