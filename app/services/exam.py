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
from app.utils.permission import PermissionHelper as permission_helper
from app.core.constants import CourseLevelEnum


class ExamService:

    def _validate_exam_association(self, exam_in):
        if not exam_in.course_id and not exam_in.curriculum_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Exam must be associated with a course or a curriculum."
            )

    def _get_course_from_exam_context(self, db: Session, exam: Optional[Exam] = None,
                                     course_id: Optional[int] = None,
                                     curriculum_id: Optional[int] = None):
        target_course_id = exam.course_id if exam else course_id
        target_curriculum_id = exam.curriculum_id if exam else curriculum_id

        if target_course_id:
            course = crud_course.get(db, id=target_course_id)
            if not course:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")
            return course

        if target_curriculum_id:
            curriculum = crud_curriculum.get(db, id=target_curriculum_id)
            if not curriculum:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Curriculum not found.")
            return curriculum.course

        return None

    def _require_exam_management_permission(self, db: Session, current_user_context: UserContext,
                                           exam: Optional[Exam] = None,
                                           course_id: Optional[int] = None,
                                           curriculum_id: Optional[int] = None):
        permission_helper.require_not_student(current_user_context, "Students cannot manage exams or questions.")

        course = self._get_course_from_exam_context(db, exam, course_id, curriculum_id)

        if not course:
            if not permission_helper.is_super_admin(current_user_context):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only Super Admin can manage exams not associated with a specific course or curriculum."
                )
            return

        permission_helper.require_course_view_permission(current_user_context, course)

        if permission_helper.is_teacher(current_user_context):
            if not permission_helper.is_teacher_of_course(current_user_context.user, course):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You must be a teacher of this course to manage exams."
                )

    def _require_exam_view_permission(self, db: Session, current_user_context: UserContext, exam: Exam):
        course = self._get_course_from_exam_context(db, exam=exam)

        if not course:
            if permission_helper.is_student(current_user_context):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Students cannot view exams not associated with a course or curriculum."
                )
            return

        permission_helper.require_course_view_permission(current_user_context, course)

    def _get_user_course_and_curriculum_ids(self, db: Session, current_user_context: UserContext):
        if permission_helper.is_super_admin(current_user_context):
            return None, None

        if permission_helper.is_school_admin(current_user_context) and current_user_context.school:
            courses = crud_course.get_courses_by_school(db, school_id=current_user_context.school.id)
        elif permission_helper.is_teacher(current_user_context):
            courses = crud_course.get_teacher_courses(db, user_id=current_user_context.user.id)
        elif permission_helper.is_student(current_user_context):
            courses = crud_course.get_student_courses(db, user_id=current_user_context.user.id)
        else:
            return [], []

        course_ids = [c.id for c in courses]
        curriculums = crud_curriculum.get_curriculums_by_course(db, course_ids=course_ids)
        curriculum_ids = [curr.id for curr in curriculums]

        return course_ids, curriculum_ids

    def create_exam(self, db: Session, exam_in: ExamCreate, current_user_context: UserContext) -> Exam:
        self._validate_exam_association(exam_in)
        self._require_exam_management_permission(
            db, current_user_context,
            course_id=exam_in.course_id,
            curriculum_id=exam_in.curriculum_id
        )

        new_exam = crud_exam.create(db, obj_in=exam_in)
        db.flush()
        return new_exam

    def get_exam(self, db: Session, exam_id: int, current_user_context: UserContext) -> Exam:
        exam = crud_exam.get(db, id=exam_id)
        if not exam:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found.")

        self._require_exam_view_permission(db, current_user_context, exam)
        return exam

    def update_exam(self, db: Session, exam_id: int, exam_in: ExamUpdate, current_user_context: UserContext) -> Exam:
        exam = crud_exam.get(db, id=exam_id)
        if not exam:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found.")

        self._require_exam_management_permission(db, current_user_context, exam=exam)

        if exam_in.course_id or exam_in.curriculum_id:
            self._require_exam_management_permission(
                db, current_user_context,
                course_id=exam_in.course_id,
                curriculum_id=exam_in.curriculum_id
            )

        updated_exam = crud_exam.update(db, db_obj=exam, obj_in=exam_in)
        return updated_exam

    def delete_exam(self, db: Session, exam_id: int, current_user_context: UserContext) -> Exam:
        exam = crud_exam.get(db, id=exam_id)
        if not exam:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found.")

        self._require_exam_management_permission(db, current_user_context, exam=exam)

        deleted_exam = crud_exam.remove(db, id=exam_id)
        return deleted_exam

    def get_all_exams(self, db: Session, current_user_context: UserContext, skip: int = 0, limit: int = 100, level: Optional[CourseLevelEnum] = None) -> List[Exam]:
        is_super_admin = permission_helper.is_super_admin(current_user_context)

        course_ids = None
        curriculum_ids = None

        if not is_super_admin:
            course_ids, curriculum_ids = self._get_user_course_and_curriculum_ids(db, current_user_context)
            if not course_ids and not curriculum_ids:
                return []

        return crud_exam.get_multi_filtered(
            db,
            skip=skip,
            limit=limit,
            level=level,
            course_ids=course_ids,
            curriculum_ids=curriculum_ids,
            is_super_admin=is_super_admin
        )

    def create_question(self, db: Session, question_in: QuestionCreate, current_user_context: UserContext) -> Question:
        exam = crud_exam.get(db, id=question_in.exam_id)
        if not exam:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found.")

        self._require_exam_management_permission(db, current_user_context, exam=exam)

        new_question = crud_question.create(db, obj_in=question_in)
        db.flush()
        return new_question

    def create_questions(self, db: Session, questions_in: List[QuestionCreate], current_user_context: UserContext) -> List[Question]:
        if not questions_in:
            return []

        exam_id = questions_in[0].exam_id
        exam = crud_exam.get(db, id=exam_id)
        if not exam:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found.")

        self._require_exam_management_permission(db, current_user_context, exam=exam)

        new_questions = crud_question.create_multi(db, objs_in=questions_in)
        db.flush()
        return new_questions

    def get_question(self, db: Session, question_id: int, current_user_context: UserContext,
                    include_correct_answer: bool = False) -> Question:
        question = crud_question.get(db, id=question_id)
        if not question:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found.")

        exam = crud_exam.get(db, id=question.exam_id)
        if not exam:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found for this question.")

        self._require_exam_view_permission(db, current_user_context, exam)

        if not include_correct_answer and permission_helper.is_student(current_user_context):
            question.correct_answer = None

        return question

    def update_question(self, db: Session, question_id: int, question_in: QuestionUpdate,
                       current_user_context: UserContext) -> Question:
        question = crud_question.get(db, id=question_id)
        if not question:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found.")

        exam = crud_exam.get(db, id=question.exam_id)
        if not exam:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found for this question.")

        self._require_exam_management_permission(db, current_user_context, exam=exam)

        updated_question = crud_question.update(db, db_obj=question, obj_in=question_in)
        return updated_question

    def delete_question(self, db: Session, question_id: int, current_user_context: UserContext) -> Question:
        question = crud_question.get(db, id=question_id)
        if not question:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found.")

        exam = crud_exam.get(db, id=question.exam_id)
        if not exam:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found for this question.")

        self._require_exam_management_permission(db, current_user_context, exam=exam)

        deleted_question = crud_question.remove(db, id=question_id)
        return deleted_question

    def get_exam_questions(self, db: Session, exam_id: int, current_user_context: UserContext,
                          include_correct_answers: bool = False) -> List[Question]:
        exam = crud_exam.get(db, id=exam_id)
        if not exam:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found.")

        self._require_exam_view_permission(db, current_user_context, exam)

        questions = crud_question.get_questions_by_exam(db, exam_id=exam_id)

        if not include_correct_answers and permission_helper.is_student(current_user_context):
            for question in questions:
                question.correct_answer = None

        return questions


exam_service = ExamService()