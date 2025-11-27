from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.constants import RoleEnum
from app.schemas.user import SuperAdminUserSummary, SuperAdminUserUpdate, User as UserSchema
from app.services.user import user_service
from app.schemas.response import APIResponse
from app.utils import deps
from app.crud.base import PaginatedResponse
from app.core.decorators import cache_endpoint
from app.core.cache import cache

router = APIRouter()

@router.get("/users", response_model=APIResponse[PaginatedResponse[SuperAdminUserSummary]], dependencies=[Depends(deps.require_role(RoleEnum.SUPER_ADMIN))])
@cache_endpoint(ttl=600)
async def get_all_users_admin(
    *,
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 50
):
    paginated_users = user_service.get_all_users_for_super_admin_paginated(db, skip=skip, limit=limit)
    return APIResponse(message="Users retrieved successfully", data=paginated_users)

@router.get("/users/{user_id}", response_model=APIResponse[UserSchema], dependencies=[Depends(deps.require_role(RoleEnum.SUPER_ADMIN))])
@cache_endpoint(ttl=300)
async def get_user_admin(
    *,
    user_id: int,
    db: Session = Depends(deps.get_db)
):
    user = user_service.get_user_for_super_admin(db, user_id)
    return APIResponse(message="User retrieved successfully", data=user)

@router.put("/users/{user_id}", response_model=APIResponse[UserSchema], dependencies=[Depends(deps.require_role(RoleEnum.SUPER_ADMIN))])
async def update_user_admin(
    *,
    user_id: int,
    update_data: SuperAdminUserUpdate,
    db: Session = Depends(deps.get_transactional_db)
):
    updated_user = await user_service.update_user_for_super_admin(db, user_id, update_data)
    await cache.clear()
    return APIResponse(message="User updated successfully", data=updated_user)

@router.delete("/users/{user_id}", response_model=APIResponse[dict], dependencies=[Depends(deps.require_role(RoleEnum.SUPER_ADMIN))])
async def delete_user_admin(
    *,
    user_id: int,
    db: Session = Depends(deps.get_transactional_db)
):
    deleted_user = await user_service.delete_user_by_admin(db, user_id)
    await cache.clear()
    return APIResponse(message="User deleted successfully")
