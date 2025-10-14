from sqlalchemy.orm import Session
from typing import List
from fastapi import HTTPException, status

from app.crud.permission import permission as crud_permission
from app.models.permission import Permission
from app.schemas.user import UserContext
from app.utils.permission import PermissionHelper as permission_helper

class PermissionService:
    def get_all_permissions(self, db: Session, current_user_context: UserContext) -> List[Permission]:
        if not permission_helper.is_super_admin(current_user_context):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Super Admins can view all permissions.")
        
        return crud_permission.get_multi(db)

permission_service = PermissionService()