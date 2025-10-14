from app.crud.base import CRUDBase
from app.models.permission import Permission
from app.schemas.permission import PermissionCreate, PermissionUpdate
from typing import List
from sqlalchemy.orm import Session

class CRUDPermission(CRUDBase[Permission, PermissionCreate, PermissionUpdate]):
    def get_multi_by_ids(self, db: Session, *, ids: List[int]) -> List[Permission]:
        return db.query(self.model).filter(self.model.id.in_(ids)).all()
    pass

permission = CRUDPermission(Permission)
