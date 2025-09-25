from sqlalchemy.orm import Session
from app.crud.role import role as crud_role
from app.crud.permission import permission as crud_permission
from app.models.role import Role
from fastapi import HTTPException, status

class RoleService:
    """Service layer for role-related business logic."""

    def assign_permission_to_role(self, db: Session, *, role_id: int, permission_id: int) -> Role:
        """Associates a permission with a role."""
        role = crud_role.get(db, id=role_id)
        if not role:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

        permission = crud_permission.get(db, id=permission_id)
        if not permission:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")

        if permission in role.permissions:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Permission already assigned to this role")

        role.permissions.append(permission)
        db.add(role)
        db.commit()
        db.refresh(role)
        return role

role_service = RoleService()
