from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.schemas.response import APIResponse
from app.utils import deps
from app.schemas.course_enrollment import CourseEnrollment
from app.schemas.lesson_progress import LessonProgress
from app.services.course_progress import course_progress_service
from app.schemas.user import UserContext
from app.core.decorators import cache_endpoint
from app.core.cache import cache

router = APIRouter()

@router.post("/courses/{course_id}/start", response_model=APIResponse[CourseEnrollment])
async def start_course(
    *,
    db: Session = Depends(deps.get_transactional_db),
    course_id: int,
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    enrollment = await course_progress_service.start_course(db, course_id=course_id, current_user_context=context)
    await cache.invalidate_user_cache(context.user.id)
    return APIResponse(message="Course started successfully", data=CourseEnrollment.model_validate(enrollment))


@router.post("/lessons/{lesson_id}/start", response_model=APIResponse[LessonProgress])
async def start_lesson(
    *,
    db: Session = Depends(deps.get_transactional_db),
    lesson_id: int,
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    progress = await course_progress_service.start_lesson(db, lesson_id=lesson_id, current_user_context=context)
    await cache.invalidate_user_cache(context.user.id)
    return APIResponse(message="Lesson started successfully", data=LessonProgress.model_validate(progress))


@router.post("/lessons/{lesson_id}/complete", response_model=APIResponse[LessonProgress])
async def complete_lesson(
    *,
    db: Session = Depends(deps.get_transactional_db),
    lesson_id: int,
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    progress = await course_progress_service.complete_lesson(db, lesson_id=lesson_id, current_user_context=context)
    await cache.invalidate_user_cache(context.user.id)
    return APIResponse(message="Lesson completed successfully", data=LessonProgress.model_validate(progress))


@router.get("/courses/{course_id}/progress", response_model=APIResponse[CourseEnrollment])
@cache_endpoint(ttl=300)
async def get_course_progress(
    *,
    db: Session = Depends(deps.get_db),
    course_id: int,
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    progress = course_progress_service.get_course_progress(db, course_id=course_id, current_user_context=context)
    return APIResponse(message="Course progress retrieved successfully", data=CourseEnrollment.model_validate(progress))


@router.get("/courses/{course_id}/completed-lessons", response_model=APIResponse[List[int]])
@cache_endpoint(ttl=300)
async def get_completed_lessons(
    *,
    db: Session = Depends(deps.get_db),
    course_id: int,
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    completed_lesson_ids = course_progress_service.get_completed_lessons(
        db, course_id=course_id, current_user_context=context
    )
    return APIResponse(message="Completed lessons retrieved successfully", data=completed_lesson_ids)


@router.get("/courses/{course_id}/lesson-progress", response_model=APIResponse[List[LessonProgress]])
@cache_endpoint(ttl=300)
async def get_lesson_progress_details(
    *,
    db: Session = Depends(deps.get_db),
    course_id: int,
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    progress = course_progress_service.get_lesson_progress_details(
        db, course_id=course_id, current_user_context=context
    )
    return APIResponse(
        message="Lesson progress details retrieved successfully",
        data=[LessonProgress.model_validate(lp) for lp in progress]
    )


@router.get("/users/{user_id}/enrollments", response_model=APIResponse[List[CourseEnrollment]])
@cache_endpoint(ttl=300)
async def get_user_enrollments(
    *,
    db: Session = Depends(deps.get_db),
    user_id: int,
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    enrollments = course_progress_service.get_user_enrollments(
        db, user_id=user_id, current_user_context=context
    )
    return APIResponse(
        message="User enrollments retrieved successfully",
        data=[CourseEnrollment.model_validate(e) for e in enrollments]
    )