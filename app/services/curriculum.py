from typing import List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.crud.curriculum import curriculum as crud_curriculum
from app.crud.course import course as crud_course
from app.crud.lesson import lesson as crud_lesson
from app.schemas.curriculum import CurriculumCreate, CurriculumUpdate, Curriculum
from app.schemas.user import UserContext
from app.core.constants import RoleEnum
from app.services.course import course_service
from app.utils.permission import PermissionHelper

class CurriculumService:
    def create_curriculum(self, db: Session, curriculum_in: CurriculumCreate, current_user_context: UserContext) -> Curriculum:
        course = crud_course.get(db, id=curriculum_in.course_id)
        if not course:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")

        PermissionHelper.require_not_student(current_user_context)
        PermissionHelper.require_course_management_permission(current_user_context, course)

        if curriculum_in.order is None:
            existing_curriculums = crud_curriculum.get_by_course(db, course_id=curriculum_in.course_id)
            curriculum_in.order = len(existing_curriculums)

        new_curriculum = crud_curriculum.create(db, obj_in=curriculum_in)
        return new_curriculum

    def get_curriculum(self, db: Session, curriculum_id: int, current_user_context: UserContext) -> Curriculum:
        curriculum = crud_curriculum.get(db, id=curriculum_id)
        if not curriculum:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Curriculum not found.")

        PermissionHelper.require_course_view_permission(current_user_context, curriculum.course)
        return curriculum

    def get_curriculums_by_course(self, db: Session, course_id: int, current_user_context: UserContext) -> List[Curriculum]:
        course = crud_course.get(db, id=course_id)
        if not course:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")

        PermissionHelper.require_course_view_permission(current_user_context, course)
        return crud_curriculum.get_by_course(db, course_id=course_id)

    async def update_curriculum(self, db: Session, curriculum_id: int, curriculum_in: CurriculumUpdate, current_user_context: UserContext) -> Curriculum:
        curriculum = crud_curriculum.get(db, id=curriculum_id)
        if not curriculum:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Curriculum not found.")

        PermissionHelper.require_not_student(current_user_context)
        PermissionHelper.require_course_management_permission(current_user_context, curriculum.course)

        updated_curriculum = crud_curriculum.update(db, db_obj=curriculum, obj_in=curriculum_in)
        return updated_curriculum

    async def delete_curriculum(self, db: Session, curriculum_id: int, current_user_context: UserContext):
        curriculum = crud_curriculum.get(db, id=curriculum_id)
        if not curriculum:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Curriculum not found.")

        PermissionHelper.require_not_student(current_user_context)
        PermissionHelper.require_course_management_permission(current_user_context, curriculum.course)

        course_id = curriculum.course_id
        school_id = curriculum.course.school_id
        
        lesson_ids = [lesson.id for lesson in curriculum.lessons]
        
        for lesson in curriculum.lessons:
            crud_lesson.delete(db, id=lesson.id)
        
        crud_curriculum.delete(db, id=curriculum_id)
        
        return {"message": "Curriculum deleted successfully", "lesson_ids": lesson_ids}

curriculum_service = CurriculumService()
