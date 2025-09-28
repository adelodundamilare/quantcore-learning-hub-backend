from typing import Optional
from requests import Session
from app.crud.base import CRUDBase
from app.models.school import School
from app.schemas.school import SchoolCreate, SchoolUpdate

class CRUDSchool(CRUDBase[School, SchoolCreate, SchoolUpdate]):
    """CRUD operations for Schools."""

    def get_by_name(self, db: Session, *, name: str) -> Optional[School]:
        return db.query(School).filter(School.name == name).first()

    pass

school = CRUDSchool(School)
