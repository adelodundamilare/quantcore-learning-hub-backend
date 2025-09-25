from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.utils import deps
from app.services.school import school_service
from app.schemas.school import School, SchoolCreate
from app.schemas.user import UserCreate
from pydantic import BaseModel

class SchoolSignupRequest(BaseModel):
    school: SchoolCreate
    admin: UserCreate

router = APIRouter()

@router.post("/school", response_model=School)
def school_signup(
    *, 
    db: Session = Depends(deps.get_db), 
    signup_request: SchoolSignupRequest
):
    """Handles the creation of a new school and its administrator."""
    return school_service.create_school_and_admin(
        db=db, 
        school_in=signup_request.school, 
        admin_in=signup_request.admin
    )
