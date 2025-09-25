from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.utils import deps
from app.services.school import school_service
from app.schemas.school import School, SchoolCreate
from app.schemas.user import UserCreate
from pydantic import BaseModel
from app.schemas.response import APIResponse

class SchoolSignupRequest(BaseModel):
    school: SchoolCreate
    admin: UserCreate

router = APIRouter()

@router.post("/school", response_model=APIResponse[School])
def school_signup(
    *, 
    db: Session = Depends(deps.get_db), 
    signup_request: SchoolSignupRequest
):
    """Handles the creation of a new school and its administrator."""
    new_school = school_service.create_school_and_admin(
        db=db, 
        school_in=signup_request.school, 
        admin_in=signup_request.admin
    )
    return APIResponse(message="School and admin created successfully", data=new_school)
