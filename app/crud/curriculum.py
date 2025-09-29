from sqlalchemy.orm import Session
from typing import List

from app.crud.base import CRUDBase
from app.models.curriculum import Curriculum
from app.schemas.curriculum import CurriculumCreate, CurriculumUpdate

class CRUDCurriculum(CRUDBase[Curriculum, CurriculumCreate, CurriculumUpdate]):
    def get_by_course(self, db: Session, *, course_id: int) -> List[Curriculum]:
        return db.query(self.model).filter(self.model.course_id == course_id).order_by(self.model.order).all()

curriculum = CRUDCurriculum(Curriculum)
