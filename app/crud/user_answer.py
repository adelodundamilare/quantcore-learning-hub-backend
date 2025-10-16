from sqlalchemy.orm import Session, selectinload
from typing import List, Optional

from app.crud.base import CRUDBase
from app.models.user_answer import UserAnswer
from app.schemas.user_answer import UserAnswerCreate, UserAnswerUpdate
class CRUDUserAnswer(CRUDBase[UserAnswer, UserAnswerCreate, UserAnswerUpdate]):

    def _query_with_relationships(self, db: Session):
        return db.query(UserAnswer).options(
            selectinload(UserAnswer.user),
            selectinload(UserAnswer.question),
            selectinload(UserAnswer.exam_attempt)
        )

    def get(self, db: Session, id: int):
        return self._query_with_relationships(db).filter(UserAnswer.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100) -> List[UserAnswer]:
        return (
            self._query_with_relationships(db)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_attempt_and_question(self, db: Session, exam_attempt_id: int,
                                    question_id: int) -> Optional[UserAnswer]:
        return (
            self._query_with_relationships(db)
            .filter(UserAnswer.exam_attempt_id == exam_attempt_id)
            .filter(UserAnswer.question_id == question_id)
            .first()
        )

    def get_all_by_attempt(self, db: Session, exam_attempt_id: int) -> List[UserAnswer]:
        return (
            self._query_with_relationships(db)
            .filter(UserAnswer.exam_attempt_id == exam_attempt_id)
            .all()
        )

    def get_all_by_user(self, db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[UserAnswer]:
        return (
            self._query_with_relationships(db)
            .filter(UserAnswer.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_correct_answers_count(self, db: Session, exam_attempt_id: int) -> int:
        return (
            self._query_with_relationships(db)
            .filter(UserAnswer.exam_attempt_id == exam_attempt_id)
            .filter(UserAnswer.is_correct == True)
            .count()
        )


user_answer = CRUDUserAnswer(UserAnswer)