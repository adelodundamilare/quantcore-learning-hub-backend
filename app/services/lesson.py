from typing import List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.crud.lesson import lesson as crud_lesson
from app.crud.curriculum import curriculum as crud_curriculum
from app.schemas.lesson import LessonCreate, LessonUpdate, Lesson
from app.schemas.user import UserContext
from app.core.constants import RoleEnum
from app.services.course import course_service

class LessonService:
    def create_lesson(self, db: Session, lesson_in: LessonCreate, current_user_context: UserContext) -> Lesson:
        curriculum = crud_curriculum.get(db, id=lesson_in.curriculum_id)
        if not curriculum:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Curriculum not found.")

        if current_user_context.role.name == RoleEnum.STUDENT:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Students cannot create lessons.")

        course_service._check_course_access(current_user_context, curriculum.course)

        if current_user_context.role.name == RoleEnum.TEACHER and not course_service._is_teacher_of_course(current_user_context.user, curriculum.course):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You must be a teacher of this course to create lessons.")

        if lesson_in.order is None:
            existing_lessons = crud_lesson.get_by_curriculum(db, curriculum_id=lesson_in.curriculum_id)
            lesson_in.order = len(existing_lessons)

        new_lesson = crud_lesson.create(db, obj_in=lesson_in)
        return new_lesson

    def get_lesson(self, db: Session, lesson_id: int, current_user_context: UserContext) -> Lesson:
        lesson = crud_lesson.get(db, id=lesson_id)
        if not lesson:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found.")

        course_service._check_course_access(current_user_context, lesson.curriculum.course, allow_student_view=True)
        return lesson

    def get_lessons_by_curriculum(self, db: Session, curriculum_id: int, current_user_context: UserContext) -> List[Lesson]:
        curriculum = crud_curriculum.get(db, id=curriculum_id)
        if not curriculum:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Curriculum not found.")

        course_service._check_course_access(current_user_context, curriculum.course, allow_student_view=True)
        return crud_lesson.get_by_curriculum(db, curriculum_id=curriculum_id)

    def update_lesson(self, db: Session, lesson_id: int, lesson_in: LessonUpdate, current_user_context: UserContext) -> Lesson:
        lesson = crud_lesson.get(db, id=lesson_id)
        if not lesson:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found.")

        if current_user_context.role.name == RoleEnum.STUDENT:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Students cannot update lessons.")

        course_service._check_course_access(current_user_context, lesson.curriculum.course)

        if current_user_context.role.name == RoleEnum.TEACHER and not course_service._is_teacher_of_course(current_user_context.user, lesson.curriculum.course):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You must be a teacher of this course to update lessons.")

        updated_lesson = crud_lesson.update(db, db_obj=lesson, obj_in=lesson_in)
        return updated_lesson

    def delete_lesson(self, db: Session, lesson_id: int, current_user_context: UserContext):
        lesson = crud_lesson.get(db, id=lesson_id)
        if not lesson:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found.")

        if current_user_context.role.name == RoleEnum.STUDENT:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Students cannot delete lessons.")

        course_service._check_course_access(current_user_context, lesson.curriculum.course)

        if current_user_context.role.name == RoleEnum.TEACHER and not course_service._is_teacher_of_course(current_user_context.user, lesson.curriculum.course):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You must be a teacher of this course to delete lessons.")

        crud_lesson.delete(db, id=lesson_id)
        return {"message": "Lesson deleted successfully"}

lesson_service = LessonService()
