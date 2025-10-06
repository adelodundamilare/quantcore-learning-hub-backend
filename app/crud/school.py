from typing import Optional
from sqlalchemy.orm import Session
from datetime import datetime
from app.crud.base import CRUDBase
from app.models.school import School
from app.schemas.school import SchoolCreate, SchoolUpdate

class CRUDSchool(CRUDBase[School, SchoolCreate, SchoolUpdate]):
    """CRUD operations for Schools."""

    def get_by_name(self, db: Session, *, name: str) -> Optional[School]:
        return db.query(School).filter(School.name == name).first()

    def get_all_schools_count(self, db: Session, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> int:
        query = db.query(School)
        if start_date:
            query = query.filter(School.created_at >= start_date)
        if end_date:
            query = query.filter(School.created_at <= end_date)
        return query.count()


school = CRUDSchool(School)
