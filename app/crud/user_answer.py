from typing import List, Optional
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.user_answer import UserAnswer
from app.schemas.user_answer import UserAnswerCreate, UserAnswerUpdate

class CRUDUserAnswer(CRUDBase[UserAnswer, UserAnswerCreate, UserAnswerUpdate]):
    def get_by_attempt_and_question(self, db: Session, *, exam_attempt_id: int, question_id: int) -> Optional[UserAnswer]:
        return db.query(self.model).filter(self.model.exam_attempt_id == exam_attempt_id, self.model.question_id == question_id).first()

    def get_all_by_attempt(self, db: Session, *, exam_attempt_id: int) -> List[UserAnswer]:
        return db.query(self.model).filter(self.model.exam_attempt_id == exam_attempt_id).all()

user_answer = CRUDUserAnswer(UserAnswer)
