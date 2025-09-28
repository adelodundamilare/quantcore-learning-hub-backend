from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.school import School, SchoolCreate
from app.core.constants import PermissionEnum
from app.schemas.response import APIResponse
from app.schemas.user import AdminSchoolInvite
from app.crud.school import school as crud_school
from app.services.user import user_service
from app.utils import deps

router = APIRouter()

@router.post("/", response_model=APIResponse[School], dependencies=[Depends(deps.require_permission(PermissionEnum.SCHOOL_CREATE))])
def create_school(
    *,
    db: Session = Depends(deps.get_transactional_db),
    invite_in: AdminSchoolInvite,
    context: deps.UserContext = Depends(deps.get_current_user_with_context),
):
    """Create a new school and its initial administrator by an existing admin."""
    school = SchoolCreate(name=invite_in.school_name)

    new_school = user_service.admin_invite_user(
        db, invited_by=context.user, school=school, invite_in=invite_in
    )

    return APIResponse(message="School and admin created successfully", data=School.model_validate(new_school))

@router.get("/{school_id}", response_model=APIResponse[School], dependencies=[Depends(deps.require_permission(PermissionEnum.SCHOOL_READ))])
def read_school(
    *,
    db: Session = Depends(deps.get_db),
    school_id: int
):
    """Get a school by ID."""
    school = crud_school.get(db=db, id=school_id)
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    return APIResponse(message="School retrieved successfully", data=school)
