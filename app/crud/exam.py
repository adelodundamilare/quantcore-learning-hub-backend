from typing import List, Optional
from sqlalchemy.orm import Session, selectinload

from app.crud.base import CRUDBase
from app.models.exam import Exam
from app.schemas.exam import ExamCreate, ExamUpdate

class CRUDExam(CRUDBase[Exam, ExamCreate, ExamUpdate]):
    def get_by_course(self, db: Session, *, course_id: int) -> List[Exam]:
        return db.query(self.model).options(selectinload(self.model.questions)).filter(self.model.course_id == course_id).all()

    def get_by_curriculum(self, db: Session, *, curriculum_id: int) -> List[Exam]:
        return db.query(self.model).options(selectinload(self.model.questions)).filter(self.model.curriculum_id == curriculum_id).all()

    def get_exams_by_course_ids(self, db: Session, *, course_ids: List[int]) -> List[Exam]:
        return db.query(self.model).options(selectinload(self.model.questions)).filter(self.model.course_id.in_(course_ids)).all()

    def get_exams_by_curriculum_ids(self, db: Session, *, curriculum_ids: List[int]) -> List[Exam]:
        return db.query(self.model).options(selectinload(self.model.questions)).filter(self.model.curriculum_id.in_(curriculum_ids)).all()

exam = CRUDExam(Exam)
