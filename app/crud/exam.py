from typing import List, Optional
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.exam import Exam
from app.schemas.exam import ExamCreate, ExamUpdate

class CRUDExam(CRUDBase[Exam, ExamCreate, ExamUpdate]):
    def get_by_course(self, db: Session, *, course_id: int) -> List[Exam]:
        return db.query(self.model).filter(self.model.course_id == course_id).all()

    def get_by_curriculum(self, db: Session, *, curriculum_id: int) -> List[Exam]:
        return db.query(self.model).filter(self.model.curriculum_id == curriculum_id).all()

exam = CRUDExam(Exam)
