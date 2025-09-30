from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.crud.exam import exam as crud_exam
from app.crud.question import question as crud_question
from app.crud.course import course as crud_course
from app.crud.curriculum import curriculum as crud_curriculum
from app.schemas.exam import ExamCreate, ExamUpdate, Exam
from app.schemas.question import QuestionCreate, QuestionUpdate, Question
from app.schemas.user import UserContext
from app.core.constants import RoleEnum
from app.services.course import course_service

class ExamService:
    def _can_manage_exam_or_question(self, db: Session, current_user_context: UserContext, exam: Optional[Exam] = None, course_id: Optional[int] = None, curriculum_id: Optional[int] = None):
        if current_user_context.role.name == RoleEnum.STUDENT:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Students cannot manage exams or questions.")

        target_course_id = None
        if exam:
            target_course_id = exam.course_id
            target_curriculum_id = exam.curriculum_id
        else:
            target_course_id = course_id
            target_curriculum_id = curriculum_id

        if target_course_id:
            course = crud_course.get(db, id=target_course_id)
            if not course:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")
            course_service._check_course_access(current_user_context, course)
            if current_user_context.role.name == RoleEnum.TEACHER and not course_service._is_teacher_of_course(current_user_context.user, course):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You must be a teacher of this course to manage exams.")
        elif target_curriculum_id:
            curriculum = crud_curriculum.get(db, id=target_curriculum_id)
            if not curriculum:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Curriculum not found.")
            course_service._check_course_access(current_user_context, curriculum.course)
            if current_user_context.role.name == RoleEnum.TEACHER and not course_service._is_teacher_of_course(current_user_context.user, curriculum.course):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You must be a teacher of this course to manage exams.")
        else:
            if current_user_context.role.name != RoleEnum.SUPER_ADMIN:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Super Admin can manage exams not associated with a specific course or curriculum.")

    def _can_view_exam_or_question(self, db: Session, current_user_context: UserContext, exam: Exam):
        if exam.course_id:
            course = crud_course.get(db, id=exam.course_id)
            course_service._check_course_access(current_user_context, course, allow_student_view=True)
        elif exam.curriculum_id:
            curriculum = crud_curriculum.get(db, id=exam.curriculum_id)
            course_service._check_course_access(current_user_context, curriculum.course, allow_student_view=True)
        else:
            if current_user_context.role.name == RoleEnum.STUDENT:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Students cannot view exams not associated with a course or curriculum.")

    def create_exam(self, db: Session, exam_in: ExamCreate, current_user_context: UserContext) -> Exam:
        self._can_manage_exam_or_question(db, current_user_context, course_id=exam_in.course_id, curriculum_id=exam_in.curriculum_id)

        if not exam_in.course_id and not exam_in.curriculum_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Exam must be associated with a course or a curriculum.")

        new_exam = crud_exam.create(db, obj_in=exam_in)
        return new_exam

    def get_exam(self, db: Session, exam_id: int, current_user_context: UserContext) -> Exam:
        exam = crud_exam.get(db, id=exam_id)
        if not exam:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found.")

        self._can_view_exam_or_question(db, current_user_context, exam)

        return exam

    def update_exam(self, db: Session, exam_id: int, exam_in: ExamUpdate, current_user_context: UserContext) -> Exam:
        exam = crud_exam.get(db, id=exam_id)
        if not exam:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found.")

        if exam_in.course_id or exam_in.curriculum_id:
            self._can_manage_exam_or_question(db, current_user_context, course_id=exam_in.course_id, curriculum_id=exam_in.curriculum_id)

        self._can_manage_exam_or_question(db, current_user_context, exam=exam)

        updated_exam = crud_exam.update(db, db_obj=exam, obj_in=exam_in)
        return updated_exam

    def delete_exam(self, db: Session, exam_id: int, current_user_context: UserContext):
        exam = crud_exam.get(db, id=exam_id)
        if not exam:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found.")

        self._can_manage_exam_or_question(db, current_user_context, exam=exam)

        crud_exam.delete(db, id=exam_id)
        return {"message": "Exam deleted successfully"}

    def create_question(self, db: Session, question_in: QuestionCreate, current_user_context: UserContext) -> Question:
        exam = crud_exam.get(db, id=question_in.exam_id)
        if not exam:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found.")

        self._can_manage_exam_or_question(db, current_user_context, exam=exam)

        new_question = crud_question.create(db, obj_in=question_in)
        return new_question

    def get_question(self, db: Session, question_id: int, current_user_context: UserContext, include_correct_answer: bool = False) -> Question:
        question = crud_question.get(db, id=question_id)
        if not question:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found.")

        exam = crud_exam.get(db, id=question.exam_id)
        if not exam:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found for this question.")

        self._can_view_exam_or_question(db, current_user_context, exam)

        if not include_correct_answer and current_user_context.role.name == RoleEnum.STUDENT:
            question.correct_answer = None

        return question

    def update_question(self, db: Session, question_id: int, question_in: QuestionUpdate, current_user_context: UserContext) -> Question:
        question = crud_question.get(db, id=question_id)
        if not question:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found.")

        exam = crud_exam.get(db, id=question.exam_id)
        if not exam:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found for this question.")

        self._can_manage_exam_or_question(db, current_user_context, exam=exam)

        updated_question = crud_question.update(db, db_obj=question, obj_in=question_in)
        return updated_question

    def delete_question(self, db: Session, question_id: int, current_user_context: UserContext):
        question = crud_question.get(db, id=question_id)
        if not question:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found.")

        exam = crud_exam.get(db, id=question.exam_id)
        if not exam:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found for this question.")

        self._can_manage_exam_or_question(db, current_user_context, exam=exam)

        crud_question.delete(db, id=question_id)
        return {"message": "Question deleted successfully"}

    def get_all_exams_for_user(self, db: Session, current_user_context: UserContext) -> List[Exam]:
        if current_user_context.role.name == RoleEnum.SUPER_ADMIN:
            return crud_exam.get_multi(db)
        elif current_user_context.role.name == RoleEnum.SCHOOL_ADMIN and current_user_context.school:
            school_courses = crud_course.get_courses_by_school(db, school_id=current_user_context.school.id)
            course_ids = [c.id for c in school_courses]
            curriculums = crud_curriculum.get_curriculums_by_course(db, course_ids=course_ids)
            curriculum_ids = [curr.id for curr in curriculums]

            exams_by_course = crud_exam.get_exams_by_course_ids(db, course_ids=course_ids)
            exams_by_curriculum = crud_exam.get_exams_by_curriculum_ids(db, curriculum_ids=curriculum_ids)
            return list(set(exams_by_course + exams_by_curriculum))

        elif current_user_context.role.name == RoleEnum.TEACHER and current_user_context.user:
            teacher_courses = crud_course.get_teacher_courses(db, user_id=current_user_context.user.id)
            course_ids = [c.id for c in teacher_courses]
            curriculums = crud_curriculum.get_curriculums_by_course(db, course_ids=course_ids)
            curriculum_ids = [curr.id for curr in curriculums]

            exams_by_course = crud_exam.get_exams_by_course_ids(db, course_ids=course_ids)
            exams_by_curriculum = crud_exam.get_exams_by_curriculum_ids(db, curriculum_ids=curriculum_ids)
            return list(set(exams_by_course + exams_by_curriculum))

        elif current_user_context.role.name == RoleEnum.STUDENT and current_user_context.user:
            student_courses = crud_course.get_student_courses(db, user_id=current_user_context.user.id)
            course_ids = [c.id for c in student_courses]
            curriculums = crud_curriculum.get_curriculums_by_course(db, course_ids=course_ids)
            curriculum_ids = [curr.id for curr in curriculums]

            exams_by_course = crud_exam.get_exams_by_course_ids(db, course_ids=course_ids)
            exams_by_curriculum = crud_exam.get_exams_by_curriculum_ids(db, curriculum_ids=curriculum_ids)
            return list(set(exams_by_course + exams_by_curriculum))
        else:
            return []

exam_service = ExamService()
