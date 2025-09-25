from sqlalchemy.orm import Session
from app.crud.role import role as crud_role
from app.crud.permission import permission as crud_permission
from app.models.role import Role

class RoleService:
    """Service layer for role-related business logic."""

    def assign_permission_to_role(self, db: Session, *, role_id: int, permission_id: int) -> Role:
        """Associates a permission with a role."""
        role = crud_role.get(db, id=role_id)
        permission = crud_permission.get(db, id=permission_id)
        if role and permission:
            role.permissions.append(permission)
            db.commit()
            db.refresh(role)
        return role

role_service = RoleService()
