from typing import List
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.question import Question
from app.schemas.question import QuestionCreate, QuestionUpdate

class CRUDQuestion(CRUDBase[Question, QuestionCreate, QuestionUpdate]):
    def get_by_exam(self, db: Session, *, exam_id: int) -> List[Question]:
        return db.query(self.model).filter(self.model.exam_id == exam_id).all()

question = CRUDQuestion(Question)
