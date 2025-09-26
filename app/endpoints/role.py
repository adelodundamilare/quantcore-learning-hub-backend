from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.response import APIResponse
from app.utils import deps
from app.crud.role import role as crud_role
from app.schemas.role import Role, RoleCreate
from app.services.role import role_service
from app.core.constants import PermissionEnum

router = APIRouter()

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

@router.post("/{role_id}/permissions/{permission_id}", response_model=APIResponse[Role], dependencies=[Depends(deps.require_permission(PermissionEnum.PERMISSION_ASSIGN))])
def assign_permission_to_role(
    *,
    db: Session = Depends(deps.get_db),
    role_id: int,
    permission_id: int
):
    """Assign a permission to a role."""
    updated_role = role_service.assign_permission_to_role(db=db, role_id=role_id, permission_id=permission_id)
    return APIResponse(message="Permission assigned to role successfully", data=updated_role)
