from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.utils import deps
from app.crud import permission as crud_permission
from app.schemas.permission import Permission, PermissionCreate
from app.core.constants import PermissionEnum
from app.schemas.response import APIResponse

router = APIRouter()

@router.post("/", response_model=APIResponse[Permission], dependencies=[Depends(deps.require_permission(PermissionEnum.PERMISSION_CREATE))])
def create_permission(
    *,
    db: Session = Depends(deps.get_db),
    permission_in: PermissionCreate
):
    """Create a new permission."""
    new_permission = crud_permission.create(db=db, obj_in=permission_in)
    return APIResponse(message="Permission created successfully", data=new_permission)

@router.get("/{permission_id}", response_model=Permission, dependencies=[Depends(deps.require_permission(PermissionEnum.PERMISSION_READ))])
def read_permission(
    *,
    db: Session = Depends(deps.get_db),
    permission_id: int
):
    """Get a permission by ID."""
    permission = crud_permission.get(db=db, id=permission_id)
    if not permission:
        raise HTTPException(status_code=404, detail="Permission not found")
    return APIResponse(message="Permission retrieved successfully", data=Permission.model_validate(permission))
