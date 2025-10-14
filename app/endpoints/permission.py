from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.utils import deps
from app.schemas.permission import Permission
from app.schemas.response import APIResponse
from app.services.permission import permission_service
from app.schemas.user import UserContext

router = APIRouter()

@router.get("/", response_model=APIResponse[List[Permission]])
def get_all_permissions(
    *,
    db: Session = Depends(deps.get_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    permissions = permission_service.get_all_permissions(db, current_user_context=context)
    return APIResponse(message="Permissions retrieved successfully", data=permissions)

# @router.post("/", response_model=APIResponse[Permission], dependencies=[Depends(deps.require_permission(PermissionEnum.PERMISSION_CREATE))])
# def create_permission(
#     *,
#     db: Session = Depends(deps.get_transactional_db),
#     permission_in: PermissionCreate
# ):
#     """Create a new permission."""
#     new_permission = crud_permission.create(db=db, obj_in=permission_in)
#     return APIResponse(message="Permission created successfully", data=new_permission)

# @router.get("/{permission_id}", response_model=Permission, dependencies=[Depends(deps.require_permission(PermissionEnum.PERMISSION_READ))])
# def read_permission(
#     *,
#     db: Session = Depends(deps.get_db),
#     permission_id: int
# ):
#     """Get a permission by ID."""
#     permission = crud_permission.get(db=db, id=permission_id)
#     if not permission:
#         raise HTTPException(status_code=404, detail="Permission not found")
#     return APIResponse(message="Permission retrieved successfully", data=Permission.model_validate(permission))
