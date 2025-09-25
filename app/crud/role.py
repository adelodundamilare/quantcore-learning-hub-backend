from app.crud.base import CRUDBase
from app.models.role import Role
from app.schemas.role import RoleCreate, RoleUpdate
from sqlalchemy.orm import Session

class CRUDRole(CRUDBase[Role, RoleCreate, RoleUpdate]):
    """CRUD operations for Roles."""
    def get_by_name(self, db: Session, *, name: str) -> Role | None:
        return db.query(Role).filter(Role.name == name).first()

    pass

role = CRUDRole(Role)
