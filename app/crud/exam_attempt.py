from sqlalchemy.orm import Session, selectinload
from typing import List
from sqlalchemy import func

from app.core.constants import ExamAttemptStatusEnum
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

    def get(self, db: Session, id: int):
        return self._query_with_relationships(db).filter(ExamAttempt.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100) -> List[ExamAttempt]:
        return (
            self._query_with_relationships(db)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_user_and_exam(self, db: Session, user_id: int, exam_id: int) -> List[ExamAttempt]:
        return (
            self._query_with_relationships(db)
            .filter(ExamAttempt.user_id == user_id)
            .filter(ExamAttempt.exam_id == exam_id)
            .order_by(ExamAttempt.start_time.desc())
            .all()
        )

    def get_all_by_user(self, db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[ExamAttempt]:
        return (
            self._query_with_relationships(db)
            .filter(ExamAttempt.user_id == user_id)
            .order_by(ExamAttempt.start_time.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_all_by_exam(self, db: Session, exam_id: int, skip: int = 0, limit: int = 100) -> List[ExamAttempt]:
        return (
            self._query_with_relationships(db)
            .filter(ExamAttempt.exam_id == exam_id)
            .order_by(ExamAttempt.start_time.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_in_progress_attempts(self, db: Session, user_id: int) -> List[ExamAttempt]:
        return (
            self._query_with_relationships(db)
            .filter(ExamAttempt.user_id == user_id)
            .filter(ExamAttempt.status == "in_progress")
            .order_by(ExamAttempt.start_time.desc())
            .all()
        )

    def get_user_average_score(self, db: Session, user_id: int) -> float:
        result = (
            db.query(func.avg(ExamAttempt.score))
            .filter(
                ExamAttempt.user_id == user_id,
                ExamAttempt.status != ExamAttemptStatusEnum.IN_PROGRESS,
                ExamAttempt.score.isnot(None)
            )
            .scalar()
        )
        return round(result, 2) if result else 0.0

    def get_user_completed_exam_ids(self, db: Session, user_id: int) -> set:
        result = (
            db.query(ExamAttempt.exam_id)
            .filter(
                ExamAttempt.user_id == user_id,
                ExamAttempt.status != ExamAttemptStatusEnum.IN_PROGRESS
            )
            .distinct()
            .all()
        )
        return {row[0] for row in result}

    def get_user_in_progress_exam_ids(self, db: Session, user_id: int) -> set:
        result = (
            db.query(ExamAttempt.exam_id)
            .filter(
                ExamAttempt.user_id == user_id,
                ExamAttempt.status == ExamAttemptStatusEnum.IN_PROGRESS
            )
            .distinct()
            .all()
        )
        return {row[0] for row in result}

    def get_user_highest_scores(self, db: Session, user_id: int) -> dict[int, float]:
        result = (
            db.query(
                ExamAttempt.exam_id,
                func.max(ExamAttempt.score)
            )
            .filter(
                ExamAttempt.user_id == user_id,
                ExamAttempt.status != ExamAttemptStatusEnum.IN_PROGRESS,
                ExamAttempt.score.isnot(None)
            )
            .group_by(ExamAttempt.exam_id)
            .all()
        )
        return {row[0]: row[1] for row in result}


exam_attempt = CRUDExamAttempt(ExamAttempt)