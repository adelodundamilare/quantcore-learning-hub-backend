from sqlalchemy.orm import Session
from typing import List

from app.crud.base import CRUDBase
from app.models.lesson import Lesson
from app.schemas.lesson import LessonCreate, LessonUpdate

class CRUDLesson(CRUDBase[Lesson, LessonCreate, LessonUpdate]):
    def get_by_curriculum(self, db: Session, *, curriculum_id: int) -> List[Lesson]:
        return db.query(self.model).filter(self.model.curriculum_id == curriculum_id).order_by(self.model.order).all()

lesson = CRUDLesson(Lesson)
