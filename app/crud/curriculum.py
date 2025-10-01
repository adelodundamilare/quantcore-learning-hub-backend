from sqlalchemy.orm import Session, selectinload
from typing import List

from app.crud.base import CRUDBase
from app.models.curriculum import Curriculum
from app.schemas.curriculum import CurriculumCreate, CurriculumUpdate

class CRUDCurriculum(CRUDBase[Curriculum, CurriculumCreate, CurriculumUpdate]):
    def get_by_course(self, db: Session, *, course_id: int) -> List[Curriculum]:
        return db.query(self.model).options(selectinload(self.model.lessons)).filter(self.model.course_id == course_id).order_by(self.model.order).all()

    def get_curriculums_by_course(self, db: Session, *, course_ids: List[int]) -> List[Curriculum]:
        return db.query(self.model).options(selectinload(self.model.lessons)).filter(self.model.course_id.in_(course_ids)).order_by(self.model.course_id, self.model.order).all()

curriculum = CRUDCurriculum(Curriculum)
