from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.schemas.user import User, StudentCourseUpdate, TeacherCourseUpdate
from app.schemas.response import APIResponse
from app.utils import deps
from app.schemas.course import Course, CourseCreate, CourseUpdate
from app.services.course import course_service
from app.schemas.user import UserContext

router = APIRouter()


@router.post("/", response_model=APIResponse[Course], status_code=status.HTTP_201_CREATED)
def create_course(
    *,
    db: Session = Depends(deps.get_transactional_db),
    course_in: CourseCreate,
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    new_course = course_service.create_course(db, course_in=course_in, current_user_context=context)
    return APIResponse(message="Course created successfully", data=Course.model_validate(new_course))


@router.get("/", response_model=APIResponse[List[Course]])
def get_all_courses(
    db: Session = Depends(deps.get_db),
    context: UserContext = Depends(deps.get_current_user_with_context),
    skip: int = 0,
    limit: int = 100
):
    courses = course_service.get_all_courses(db, current_user_context=context, skip=skip, limit=limit)
    return APIResponse(message="Courses retrieved successfully", data=[Course.model_validate(c) for c in courses])


@router.get("/me", response_model=APIResponse[List[Course]])
def get_my_courses(
    db: Session = Depends(deps.get_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    courses = course_service.get_user_courses(db, current_user_context=context)
    return APIResponse(message="Your courses retrieved successfully", data=[Course.model_validate(c) for c in courses])


@router.get("/by-school/{school_id}", response_model=APIResponse[List[Course]])
def get_courses_by_school(
    school_id: int,
    db: Session = Depends(deps.get_db),
    context: UserContext = Depends(deps.get_current_user_with_context),
    skip: int = 0,
    limit: int = 100
):
    courses = course_service.get_courses_by_school_id(db, school_id=school_id, current_user_context=context, skip=skip, limit=limit)
    return APIResponse(message="Courses for school retrieved successfully", data=[Course.model_validate(c) for c in courses])


@router.get("/{course_id}", response_model=APIResponse[Course])
def read_course(
    *,
    db: Session = Depends(deps.get_db),
    course_id: int,
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    course = course_service.get_course(db, course_id=course_id, current_user_context=context)
    return APIResponse(message="Course retrieved successfully", data=Course.model_validate(course))


@router.put("/{course_id}", response_model=APIResponse[Course])
def update_course(
    *,
    db: Session = Depends(deps.get_transactional_db),
    course_id: int,
    course_in: CourseUpdate,
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    updated_course = course_service.update_course(db, course_id=course_id, course_in=course_in, current_user_context=context)
    return APIResponse(message="Course updated successfully", data=Course.model_validate(updated_course))


@router.delete("/{course_id}", response_model=APIResponse[Course])
def delete_course(
    *,
    db: Session = Depends(deps.get_transactional_db),
    course_id: int,
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    deleted_course = course_service.delete_course(db, course_id=course_id, current_user_context=context)
    return APIResponse(message="Course deleted successfully", data=Course.model_validate(deleted_course))


@router.get("/{course_id}/teachers", response_model=APIResponse[List[User]])
def get_course_teachers(
    *,
    db: Session = Depends(deps.get_db),
    course_id: int,
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    teachers = course_service.get_course_teachers(db, course_id=course_id, current_user_context=context)
    return APIResponse(message="Course teachers retrieved successfully", data=[User.model_validate(u) for u in teachers])


@router.get("/{course_id}/students", response_model=APIResponse[List[User]])
def get_course_students(
    *,
    db: Session = Depends(deps.get_db),
    course_id: int,
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    students = course_service.get_course_students(db, course_id=course_id, current_user_context=context)
    return APIResponse(message="Course students retrieved successfully", data=[User.model_validate(u) for u in students])


@router.post("/{course_id}/teachers/{user_id}", response_model=APIResponse[Course])
def assign_teacher_to_course(
    *,
    db: Session = Depends(deps.get_transactional_db),
    course_id: int,
    user_id: int,
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    updated_course = course_service.assign_teacher(db, course_id=course_id, user_id=user_id, current_user_context=context)
    return APIResponse(message="Teacher assigned to course successfully", data=Course.model_validate(updated_course))


@router.delete("/{course_id}/teachers/{user_id}", response_model=APIResponse[Course])
def remove_teacher_from_course(
    *,
    db: Session = Depends(deps.get_transactional_db),
    course_id: int,
    user_id: int,
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    updated_course = course_service.remove_teacher(db, course_id=course_id, user_id=user_id, current_user_context=context)
    return APIResponse(message="Teacher removed from course successfully", data=Course.model_validate(updated_course))


@router.post("/{course_id}/students/{user_id}", response_model=APIResponse[Course])
def enroll_student_in_course(
    *,
    db: Session = Depends(deps.get_transactional_db),
    course_id: int,
    user_id: int,
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    updated_course = course_service.enroll_student(db, course_id=course_id, user_id=user_id, current_user_context=context)
    return APIResponse(message="Student enrolled in course successfully", data=Course.model_validate(updated_course))

@router.delete("/{course_id}/students/{user_id}", response_model=APIResponse[Course])
def remove_student_from_course(
    *,
    db: Session = Depends(deps.get_transactional_db),
    course_id: int,
    user_id: int,
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    updated_course = course_service.unenroll_student(db, course_id=course_id, user_id=user_id, current_user_context=context)
    return APIResponse(message="Student removed from course successfully", data=Course.model_validate(updated_course))

@router.get("/students/{student_id}/courses", response_model=APIResponse[List[Course]])
def get_student_courses_admin(
    student_id: int,
    db: Session = Depends(deps.get_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    courses = course_service.get_student_courses_admin(db, student_id=student_id, current_user_context=context)
    return APIResponse(message="Student courses retrieved successfully", data=[Course.model_validate(c) for c in courses])

@router.put("/students/{student_id}/courses", response_model=APIResponse[dict])
def update_student_courses_bulk(
    student_id: int,
    course_update: StudentCourseUpdate,
    db: Session = Depends(deps.get_transactional_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    result = course_service.update_student_courses_bulk(
        db, student_id=student_id, course_ids=course_update.course_ids, current_user_context=context
    )
    return APIResponse(
        message=f"Student courses updated: {result['enrolled_count']} enrolled, {result['unenrolled_count']} unenrolled",
        data=result
    )

@router.get("/teachers/{teacher_id}/courses", response_model=APIResponse[List[Course]])
def get_teacher_courses_admin(
    teacher_id: int,
    db: Session = Depends(deps.get_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    courses = course_service.get_teacher_courses_admin(db, teacher_id=teacher_id, current_user_context=context)
    return APIResponse(message="Teacher courses retrieved successfully", data=[Course.model_validate(c) for c in courses])

@router.put("/teachers/{teacher_id}/courses", response_model=APIResponse[dict])
def update_teacher_courses_bulk(
    teacher_id: int,
    course_update: TeacherCourseUpdate,
    db: Session = Depends(deps.get_transactional_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    result = course_service.update_teacher_courses_bulk(
        db, teacher_id=teacher_id, course_ids=course_update.course_ids, current_user_context=context
    )
    return APIResponse(
        message=f"Teacher courses updated: {result['assigned_count']} assigned, {result['removed_count']} removed",
        data=result
    )
