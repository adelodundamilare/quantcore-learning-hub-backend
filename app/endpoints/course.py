from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.schemas.response import APIResponse
from app.utils import deps
from app.schemas.course import Course, CourseCreate
from app.services.course import course_service
from app.crud.course import course as crud_course
from app.schemas.user import UserContext
from app.core.constants import RoleEnum

router = APIRouter()

@router.post("/", response_model=APIResponse[Course])
def create_course(
    *,
    db: Session = Depends(deps.get_transactional_db),
    course_in: CourseCreate,
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    """Create a new course."""
    new_course = course_service.create_course(db, course_in=course_in, current_user_context=context)
    return APIResponse(message="Course created successfully", data=Course.model_validate(new_course))


@router.get("/", response_model=APIResponse[List[Course]])
def get_all_courses(
    db: Session = Depends(deps.get_db),
    context: UserContext = Depends(deps.get_current_user_with_context),
    skip: int = 0,
    limit: int = 100
):
    """Retrieve all courses accessible to the current user."""
    courses = course_service.get_all_courses(db, current_user_context=context, skip=skip, limit=limit)
    return APIResponse(message="Courses retrieved successfully", data=[Course.model_validate(c) for c in courses])

@router.get("/me", response_model=APIResponse[List[Course]])
def get_my_courses(
    db: Session = Depends(deps.get_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    """Retrieve courses where the current user is a teacher or student."""
    courses = course_service.get_user_courses(db, current_user_context=context)
    return APIResponse(message="Your courses retrieved successfully", data=[Course.model_validate(c) for c in courses])

@router.get("/{course_id}", response_model=APIResponse[Course])
def read_course(
    *,
    db: Session = Depends(deps.get_db),
    course_id: int,
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    """Get a course by ID."""
    course = crud_course.get(db, id=course_id)
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")

    # Permission check for reading course
    if context.role.name != RoleEnum.SUPER_ADMIN and course.school_id != context.school.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to view this course.")

    return APIResponse(message="Course retrieved successfully", data=Course.model_validate(course))

@router.post("/{course_id}/teachers/{user_id}", response_model=APIResponse[Course])
def assign_teacher_to_course(
    *,
    db: Session = Depends(deps.get_transactional_db),
    course_id: int,
    user_id: int,
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    """Assign a teacher to a course."""
    updated_course = course_service.assign_teacher(db, course_id=course_id, user_id=user_id, current_user_context=context)
    return APIResponse(message="Teacher assigned to course successfully", data=Course.model_validate(updated_course))

@router.post("/{course_id}/students/{user_id}", response_model=APIResponse[Course])
def enroll_student_in_course(
    *,
    db: Session = Depends(deps.get_transactional_db),
    course_id: int,
    user_id: int,
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    """Enroll a student in a course."""
    updated_course = course_service.enroll_student(db, course_id=course_id, user_id=user_id, current_user_context=context)
    return APIResponse(message="Student enrolled in course successfully", data=Course.model_validate(updated_course))

@router.get("/by-school/{school_id}", response_model=APIResponse[List[Course]])
def get_courses_by_school(
    school_id: int,
    db: Session = Depends(deps.get_db),
    context: UserContext = Depends(deps.get_current_user_with_context),
    skip: int = 0,
    limit: int = 100
):
    """Retrieve courses for a specific school."""
    courses = course_service.get_courses_by_school_id(db, school_id=school_id, current_user_context=context, skip=skip, limit=limit)
    return APIResponse(message="Courses for school retrieved successfully", data=[Course.model_validate(c) for c in courses])
