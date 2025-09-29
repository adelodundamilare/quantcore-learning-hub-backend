from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.schemas.response import APIResponse
from app.utils import deps
from app.schemas.curriculum import Curriculum, CurriculumCreate, CurriculumUpdate
from app.schemas.lesson import Lesson, LessonCreate, LessonUpdate
from app.services.curriculum import curriculum_service
from app.services.lesson import lesson_service
from app.schemas.user import UserContext

router = APIRouter()

@router.post("/courses/{course_id}/curriculums/", response_model=APIResponse[Curriculum])
def create_curriculum(
    course_id: int,
    curriculum_in: CurriculumCreate,
    db: Session = Depends(deps.get_transactional_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    if curriculum_in.course_id != course_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Course ID in path and body must match.")
    new_curriculum = curriculum_service.create_curriculum(db, curriculum_in=curriculum_in, current_user_context=context)
    return APIResponse(message="Curriculum created successfully", data=Curriculum.model_validate(new_curriculum))

@router.get("/courses/{course_id}/curriculums/", response_model=APIResponse[List[Curriculum]])
def get_curriculums_by_course(
    course_id: int,
    db: Session = Depends(deps.get_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    curriculums = curriculum_service.get_curriculums_by_course(db, course_id=course_id, current_user_context=context)
    return APIResponse(message="Curriculums retrieved successfully", data=[Curriculum.model_validate(c) for c in curriculums])

@router.get("/courses/{course_id}/curriculums/{curriculum_id}", response_model=APIResponse[Curriculum])
def get_curriculum(
    course_id: int,
    curriculum_id: int,
    db: Session = Depends(deps.get_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    curriculum = curriculum_service.get_curriculum(db, curriculum_id=curriculum_id, current_user_context=context)
    if curriculum.course_id != course_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Curriculum does not belong to the specified course.")
    return APIResponse(message="Curriculum retrieved successfully", data=Curriculum.model_validate(curriculum))

@router.put("/courses/{course_id}/curriculums/{curriculum_id}", response_model=APIResponse[Curriculum])
def update_curriculum(
    course_id: int,
    curriculum_id: int,
    curriculum_in: CurriculumUpdate,
    db: Session = Depends(deps.get_transactional_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    curriculum = curriculum_service.get_curriculum(db, curriculum_id=curriculum_id, current_user_context=context)
    if curriculum.course_id != course_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Curriculum does not belong to the specified course.")
    updated_curriculum = curriculum_service.update_curriculum(db, curriculum_id=curriculum_id, curriculum_in=curriculum_in, current_user_context=context)
    return APIResponse(message="Curriculum updated successfully", data=Curriculum.model_validate(updated_curriculum))

@router.delete("/courses/{course_id}/curriculums/{curriculum_id}", response_model=APIResponse)
def delete_curriculum(
    course_id: int,
    curriculum_id: int,
    db: Session = Depends(deps.get_transactional_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    curriculum = curriculum_service.get_curriculum(db, curriculum_id=curriculum_id, current_user_context=context)
    if curriculum.course_id != course_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Curriculum does not belong to the specified course.")
    response = curriculum_service.delete_curriculum(db, curriculum_id=curriculum_id, current_user_context=context)
    return APIResponse(message=response["message"])

@router.post("/courses/{course_id}/curriculums/{curriculum_id}/lessons/", response_model=APIResponse[Lesson])
def create_lesson(
    course_id: int,
    curriculum_id: int,
    lesson_in: LessonCreate,
    db: Session = Depends(deps.get_transactional_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    curriculum = curriculum_service.get_curriculum(db, curriculum_id=curriculum_id, current_user_context=context)
    if curriculum.course_id != course_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Curriculum does not belong to the specified course.")
    if lesson_in.curriculum_id != curriculum_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Curriculum ID in path and body must match.")
    new_lesson = lesson_service.create_lesson(db, lesson_in=lesson_in, current_user_context=context)
    return APIResponse(message="Lesson created successfully", data=Lesson.model_validate(new_lesson))

@router.get("/courses/{course_id}/curriculums/{curriculum_id}/lessons/", response_model=APIResponse[List[Lesson]])
def get_lessons_by_curriculum(
    course_id: int,
    curriculum_id: int,
    db: Session = Depends(deps.get_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    curriculum = curriculum_service.get_curriculum(db, curriculum_id=curriculum_id, current_user_context=context)
    if curriculum.course_id != course_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Curriculum does not belong to the specified course.")
    lessons = lesson_service.get_lessons_by_curriculum(db, curriculum_id=curriculum_id, current_user_context=context)
    return APIResponse(message="Lessons retrieved successfully", data=[Lesson.model_validate(l) for l in lessons])

@router.get("/courses/{course_id}/curriculums/{curriculum_id}/lessons/{lesson_id}", response_model=APIResponse[Lesson])
def get_lesson(
    course_id: int,
    curriculum_id: int,
    lesson_id: int,
    db: Session = Depends(deps.get_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    lesson = lesson_service.get_lesson(db, lesson_id=lesson_id, current_user_context=context)
    if lesson.curriculum.course_id != course_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Lesson does not belong to the specified course.")
    if lesson.curriculum_id != curriculum_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Lesson does not belong to the specified curriculum.")
    return APIResponse(message="Lesson retrieved successfully", data=Lesson.model_validate(lesson))

@router.put("/courses/{course_id}/curriculums/{curriculum_id}/lessons/{lesson_id}", response_model=APIResponse[Lesson])
def update_lesson(
    course_id: int,
    curriculum_id: int,
    lesson_id: int,
    lesson_in: LessonUpdate,
    db: Session = Depends(deps.get_transactional_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    lesson = lesson_service.get_lesson(db, lesson_id=lesson_id, current_user_context=context)
    if lesson.curriculum.course_id != course_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Lesson does not belong to the specified course.")
    if lesson.curriculum_id != curriculum_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Lesson does not belong to the specified curriculum.")
    updated_lesson = lesson_service.update_lesson(db, lesson_id=lesson_id, lesson_in=lesson_in, current_user_context=context)
    return APIResponse(message="Lesson updated successfully", data=Lesson.model_validate(updated_lesson))

@router.delete("/courses/{course_id}/curriculums/{curriculum_id}/lessons/{lesson_id}", response_model=APIResponse)
def delete_lesson(
    course_id: int,
    curriculum_id: int,
    lesson_id: int,
    db: Session = Depends(deps.get_transactional_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    lesson = lesson_service.get_lesson(db, lesson_id=lesson_id, current_user_context=context)
    if lesson.curriculum.course_id != course_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Lesson does not belong to the specified course.")
    if lesson.curriculum_id != curriculum_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Lesson does not belong to the specified curriculum.")
    response = lesson_service.delete_lesson(db, lesson_id=lesson_id, current_user_context=context)
    return APIResponse(message=response["message"])
