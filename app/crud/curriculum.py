from sqlalchemy.orm import Session, selectinload
from typing import Any, List, Optional

from app.crud.base import CRUDBase
from app.models.curriculum import Curriculum
from app.schemas.curriculum import CurriculumCreate, CurriculumUpdate

class CRUDCurriculum(CRUDBase[Curriculum, CurriculumCreate, CurriculumUpdate]):
    def get(self, db: Session, id: Any) -> Optional[Curriculum]:
        query = db.query(self.model).filter(self.model.id == id)
        if hasattr(self.model, 'deleted_at'):
            query = query.filter(self.model.deleted_at == None)
        return query.options(selectinload(self.model.course)).first()

    def get_by_course(self, db: Session, *, course_id: int) -> List[Curriculum]:
        return db.query(self.model).options(selectinload(self.model.lessons)).filter(self.model.course_id == course_id, self.model.deleted_at == None).order_by(self.model.order).all()

    def get_curriculums_by_course(self, db: Session, *, course_ids: List[int]) -> List[Curriculum]:
        return db.query(self.model).options(selectinload(self.model.lessons)).filter(self.model.course_id.in_(course_ids), self.model.deleted_at == None).order_by(self.model.course_id, self.model.order).all()

curriculum = CRUDCurriculum(Curriculum)
