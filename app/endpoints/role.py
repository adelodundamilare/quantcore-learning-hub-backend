from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.response import APIResponse
from app.utils import deps
from app.crud.role import role as crud_role
from app.schemas.role import Role, RoleCreate, RolePermissionUpdate
from app.services.role import role_service
from app.core.constants import PermissionEnum
from app.schemas.user import UserContext

router = APIRouter()
@router.get("/", response_model=APIResponse[List[Role]])
def read_roles(
    *,
    db: Session = Depends(deps.get_db),
):
    """Get all roles."""
    roles = crud_role.get_multi(db=db)
    return APIResponse(message="Roles retrieved successfully", data=roles)

@router.post("/", response_model=APIResponse[Role], dependencies=[Depends(deps.require_permission(PermissionEnum.ROLE_CREATE))])
def create_role(
    *,
    db: Session = Depends(deps.get_transactional_db),
    role_in: RoleCreate
):
    """Create a new role."""
    new_role = crud_role.create(db=db, obj_in=role_in)
    return APIResponse(message="Role created successfully", data=Role.model_validate(new_role))

@router.get("/{role_id}", response_model=APIResponse[Role])
def read_role(
    *,
    db: Session = Depends(deps.get_db),
    role_id: int
):
    """Get a role by ID."""
    role = crud_role.get(db=db, id=role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return APIResponse(message="Role retrieved successfully", data=role)


@router.put("/{role_id}/permissions", response_model=APIResponse[Role])
def update_role_permissions(
    *,
    db: Session = Depends(deps.get_transactional_db),
    role_id: int,
    permissions_in: RolePermissionUpdate,
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    updated_role = role_service.update_role_permissions(
        db=db,
        role_id=role_id,
        permission_ids=permissions_in.permission_ids,
        current_user_context=context
    )
    return APIResponse(message="Role permissions updated successfully", data=updated_role)

@router.post("/{role_id}/permissions/{permission_id}", response_model=APIResponse[Role], dependencies=[Depends(deps.require_permission(PermissionEnum.PERMISSION_ASSIGN))])
def assign_permission_to_role(
    *,
    db: Session = Depends(deps.get_db),
    role_id: int,
    permission_id: int,
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    """Assign a permission to a role."""
    updated_role = role_service.assign_permission_to_role(db=db, role_id=role_id, permission_id=permission_id,
        current_user_context=context)
    return APIResponse(message="Permission assigned to role successfully", data=updated_role)
