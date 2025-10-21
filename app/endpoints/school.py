from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.school import School, AdminSchoolDataSchema
from app.services.school import school_service
from app.schemas.response import APIResponse
from app.schemas.user import AdminSchoolInvite, TeacherUpdate, User as UserSchema, UserContext, StudentProfile
from app.crud.school import school as crud_school
from app.services.user import user_service
from app.utils import deps
from app.crud.base import PaginatedResponse

router = APIRouter()

@router.post("/", response_model=APIResponse[None])
def create_school(
    *,
    db: Session = Depends(deps.get_transactional_db),
    invite_in: AdminSchoolInvite,
    context: deps.UserContext = Depends(deps.get_current_user_with_context),
):
    """Create a new school and its initial administrator by an existing admin."""

    new_school = user_service.admin_invite_user(
        db, invite_in=invite_in
    )

    return APIResponse(message="School and admin created successfully")

@router.get("/{school_id}", response_model=APIResponse[School])
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

@router.get("/{school_id}/students", response_model=APIResponse[List[UserSchema]])
def get_school_students(
    school_id: int,
    db: Session = Depends(deps.get_db),
    context: UserContext = Depends(deps.get_current_user_with_context),
    skip: int = 0,
    limit: int = 100
):
    """Retrieve all students for a specific school."""
    students = user_service.get_students_for_school(db, school_id=school_id, current_user_context=context, skip=skip, limit=limit)
    return APIResponse(message="Students for school retrieved successfully", data=[UserSchema.model_validate(u) for u in students])

@router.get("/{school_id}/teachers", response_model=APIResponse[List[UserSchema]])
def get_school_teachers(
    school_id: int,
    db: Session = Depends(deps.get_db),
    context: UserContext = Depends(deps.get_current_user_with_context),
    skip: int = 0,
    limit: int = 100
):
    teachers = user_service.get_teachers_for_school(db, school_id=school_id, current_user_context=context, skip=skip, limit=limit)
    return APIResponse(message="Teachers for school retrieved successfully", data=[UserSchema.model_validate(u) for u in teachers])


@router.put("/{school_id}/teachers/{teacher_id}", response_model=APIResponse[UserSchema])
def update_teacher_details(
    school_id: int,
    teacher_id: int,
    update_data: TeacherUpdate,
    db: Session = Depends(deps.get_transactional_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    """Update a teacher's level in a specific school."""
    updated_teacher = user_service.update_teacher_details(db, school_id=school_id, teacher_id=teacher_id, update_data=update_data, current_user_context=context)
    return APIResponse(message="Teacher details updated successfully", data=UserSchema.model_validate(updated_teacher))


@router.get("/{school_id}/teams", response_model=APIResponse[List[UserSchema]])
def get_school_teams(
    school_id: int,
    db: Session = Depends(deps.get_db),
    context: UserContext = Depends(deps.get_current_user_with_context),
    skip: int = 0,
    limit: int = 100
):
    teams = user_service.get_teams_for_school(db, school_id=school_id, current_user_context=context, skip=skip, limit=limit)
    return APIResponse(message="Teams for school retrieved successfully", data=[UserSchema.model_validate(u) for u in teams])


@router.get("/admin/schools/report", response_model=APIResponse[PaginatedResponse[AdminSchoolDataSchema]])
def get_admin_schools_report(
    *,
    db: Session = Depends(deps.get_db),
    context: UserContext = Depends(deps.get_current_user_with_context),
    skip: int = 0,
    limit: int = 100
):
    report_data = school_service.get_admin_schools_report(db, current_user_context=context, skip=skip, limit=limit)
    return APIResponse(message="Admin schools report retrieved successfully", data=report_data)


@router.get("/{school_id}/users/{user_id}", response_model=APIResponse[UserSchema])
def get_school_user_profile(
    school_id: int,
    user_id: int,
    db: Session = Depends(deps.get_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    user_profile = user_service.get_user_profile_for_school(
        db, school_id=school_id, user_id=user_id, current_user_context=context
    )
    return APIResponse(message="User profile retrieved successfully", data=UserSchema.model_validate(user_profile))

@router.get("/{school_id}/students/{student_id}", response_model=APIResponse[StudentProfile])
def get_school_student_profile(
    school_id: int,
    student_id: int,
    db: Session = Depends(deps.get_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    student_profile = user_service.get_student_profile_for_school(
        db, school_id=school_id, student_id=student_id, current_user_context=context
    )
    return APIResponse(message="Student profile retrieved successfully", data=student_profile)

@router.get("/{school_id}/teachers/{teacher_id}", response_model=APIResponse[UserSchema])
def get_school_teacher_profile(
    school_id: int,
    teacher_id: int,
    db: Session = Depends(deps.get_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    teacher_profile = user_service.get_teacher_profile_for_school(
        db, school_id=school_id, teacher_id=teacher_id, current_user_context=context
    )
    return APIResponse(message="Teacher profile retrieved successfully", data=UserSchema.model_validate(teacher_profile))
