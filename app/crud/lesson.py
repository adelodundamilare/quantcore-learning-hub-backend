from sqlalchemy.orm import Session, selectinload
from typing import Any, List, Optional

from app.crud.base import CRUDBase
from app.models.lesson import Lesson
from app.schemas.lesson import LessonCreate, LessonUpdate

class CRUDLesson(CRUDBase[Lesson, LessonCreate, LessonUpdate]):
    def get(self, db: Session, id: Any) -> Optional[Lesson]:
        query = db.query(self.model).filter(self.model.id == id)
        if hasattr(self.model, 'deleted_at'):
            query = query.filter(self.model.deleted_at == None)
        return query.options(selectinload(self.model.curriculum)).first()

    def get_by_curriculum(self, db: Session, *, curriculum_id: int) -> List[Lesson]:
        return db.query(self.model).filter(self.model.curriculum_id == curriculum_id, self.model.deleted_at == None).order_by(self.model.order).all()

lesson = CRUDLesson(Lesson)
