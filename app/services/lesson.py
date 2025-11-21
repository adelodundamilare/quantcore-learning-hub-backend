from typing import List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.crud.lesson import lesson as crud_lesson
from app.crud.curriculum import curriculum as crud_curriculum
from app.schemas.lesson import LessonCreate, LessonUpdate, Lesson
from app.schemas.user import UserContext
from app.core.constants import RoleEnum
from app.services.course import course_service
from app.services import cache_service
from app.utils.permission import PermissionHelper

class LessonService:
    async def create_lesson(self, db: Session, lesson_in: LessonCreate, current_user_context: UserContext) -> Lesson:
        curriculum = crud_curriculum.get(db, id=lesson_in.curriculum_id)
        if not curriculum:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Curriculum not found.")

        PermissionHelper.require_not_student(current_user_context)
        PermissionHelper.require_course_management_permission(current_user_context, curriculum.course)

        if lesson_in.order is None:
            existing_lessons = crud_lesson.get_by_curriculum(db, curriculum_id=lesson_in.curriculum_id)
            lesson_in.order = len(existing_lessons)

        new_lesson = crud_lesson.create(db, obj_in=lesson_in)
        await cache_service.invalidate_course_cache(curriculum.course.id, curriculum.course.school_id)
        return new_lesson

    def get_lesson(self, db: Session, lesson_id: int, current_user_context: UserContext) -> Lesson:
        lesson = crud_lesson.get(db, id=lesson_id)
        if not lesson:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found.")

        PermissionHelper.require_course_view_permission(current_user_context, lesson.curriculum.course)
        return lesson

    def get_lessons_by_curriculum(self, db: Session, curriculum_id: int, current_user_context: UserContext) -> List[Lesson]:
        curriculum = crud_curriculum.get(db, id=curriculum_id)
        if not curriculum:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Curriculum not found.")

        PermissionHelper.require_course_view_permission(current_user_context, curriculum.course)
        return crud_lesson.get_by_curriculum(db, curriculum_id=curriculum_id)

    async def update_lesson(self, db: Session, lesson_id: int, lesson_in: LessonUpdate, current_user_context: UserContext) -> Lesson:
        lesson = crud_lesson.get(db, id=lesson_id)
        if not lesson:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found.")

        PermissionHelper.require_not_student(current_user_context)
        PermissionHelper.require_course_management_permission(current_user_context, lesson.curriculum.course)

        updated_lesson = crud_lesson.update(db, db_obj=lesson, obj_in=lesson_in)
        await cache_service.invalidate_course_cache(lesson.curriculum.course.id, lesson.curriculum.course.school_id)
        return updated_lesson

    async def delete_lesson(self, db: Session, lesson_id: int, current_user_context: UserContext):
        lesson = crud_lesson.get(db, id=lesson_id)
        if not lesson:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found.")

        PermissionHelper.require_not_student(current_user_context)
        PermissionHelper.require_course_management_permission(current_user_context, lesson.curriculum.course)

        course_id = lesson.curriculum.course.id
        school_id = lesson.curriculum.course.school_id
        crud_lesson.delete(db, id=lesson_id)
        await cache_service.invalidate_course_cache(course_id, school_id)
        return {"message": "Lesson deleted successfully"}

lesson_service = LessonService()
