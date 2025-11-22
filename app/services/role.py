import asyncio
from sqlalchemy.orm import Session
from app.crud.role import role as crud_role
from app.crud.permission import permission as crud_permission
from app.models.role import Role
from fastapi import HTTPException, status
from typing import List

from app.schemas.user import UserContext
from app.utils.permission import PermissionHelper as permission_helper
from app.core.constants import RoleEnum
from app.core.cache import cache

class RoleService:
    def update_role_permissions(self, db: Session, *, role_id: int, permission_ids: List[int], current_user_context: UserContext) -> Role:
        if not permission_helper.is_super_admin(current_user_context):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Super Admins can manage role permissions.")

        role = crud_role.get(db, id=role_id)
        if not role:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

        if role.name == RoleEnum.SUPER_ADMIN:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot modify permissions for the Super Admin role.")

        # Remove duplicates and fetch permissions from DB
        unique_permission_ids = list(set(permission_ids))
        permissions = crud_permission.get_multi_by_ids(db, ids=unique_permission_ids)

        if len(permissions) != len(unique_permission_ids):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="One or more permission IDs are invalid.")

        result = crud_role.update_permissions(db, role=role, permissions=permissions)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(cache.delete(f"role:permissions:{role_id}"))
        loop.run_until_complete(cache.delete("permissions:all"))
        return result

    def assign_permission_to_role(self, db: Session, *, role_id: int, permission_id: int, current_user_context: UserContext) -> Role:
        if not permission_helper.is_super_admin(current_user_context):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Super Admins can manage role permissions.")

        role = crud_role.get(db, id=role_id)
        if not role:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

        permission = crud_permission.get(db, id=permission_id)
        if not permission:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")

        if permission in role.permissions:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Permission already assigned to this role")

        result = crud_role.add_permission(db, role=role, permission=permission)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(cache.delete(f"role:permissions:{role_id}"))
        loop.run_until_complete(cache.delete("permissions:all"))
        return result

role_service = RoleService()
