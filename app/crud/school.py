from app.crud.base import CRUDBase
from app.models.school import School
from app.schemas.school import SchoolCreate, SchoolUpdate

class CRUDSchool(CRUDBase[School, SchoolCreate, SchoolUpdate]):
    """CRUD operations for Schools."""
    pass

school = CRUDSchool(School)
