from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.response import APIResponse
from app.utils import deps
from app.crud import school as crud_school
from app.schemas.school import School, SchoolCreate
from app.core.constants import PermissionEnum

router = APIRouter()

@router.post("/", response_model=APIResponse[School], dependencies=[Depends(deps.require_permission(PermissionEnum.SCHOOL_CREATE))])
def create_school(
    *, 
    db: Session = Depends(deps.get_transactional_db), 
    school_in: SchoolCreate
):
    """Create a new school."""
    new_school = crud_school.create(db=db, obj_in=school_in)
    return APIResponse(message="School created successfully", data=School.model_validate(new_school))

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
