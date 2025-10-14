from app.crud.base import CRUDBase
from app.models.role import Role
from app.schemas.role import RoleCreate, RoleUpdate
from sqlalchemy.orm import Session
from typing import List
from app.models.permission import Permission

class CRUDRole(CRUDBase[Role, RoleCreate, RoleUpdate]):
    def get_by_name(self, db: Session, *, name: str) -> Role | None:
        return db.query(Role).filter(Role.name == name).first()

    def update_permissions(self, db: Session, *, role: Role, permissions: List[Permission]) -> Role:
        role.permissions = permissions
        db.add(role)
        db.commit()
        db.refresh(role)
        return role

    def add_permission(self, db: Session, *, role: Role, permission: Permission) -> Role:
        role.permissions.append(permission)
        db.add(role)
        db.commit()
        db.refresh(role)
        return role

role = CRUDRole(Role)
