from typing import List
from sqlalchemy.orm import Session, selectinload

from app.crud.base import CRUDBase
from app.models.exam_attempt import ExamAttempt
from app.schemas.exam_attempt import ExamAttemptCreate, ExamAttemptUpdate

class CRUDExamAttempt(CRUDBase[ExamAttempt, ExamAttemptCreate, ExamAttemptUpdate]):
    def get_by_user_and_exam(self, db: Session, *, user_id: int, exam_id: int) -> List[ExamAttempt]:
        return db.query(self.model).options(selectinload(self.model.user_answers)).filter(self.model.user_id == user_id, self.model.exam_id == exam_id).all()

    def get_all_by_user(self, db: Session, *, user_id: int) -> List[ExamAttempt]:
        return db.query(self.model).options(selectinload(self.model.user_answers)).filter(self.model.user_id == user_id).all()

exam_attempt = CRUDExamAttempt(ExamAttempt)
