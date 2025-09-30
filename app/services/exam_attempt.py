from typing import Any, List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime

from app.crud.exam import exam as crud_exam
from app.crud.question import question as crud_question
from app.crud.exam_attempt import exam_attempt as crud_exam_attempt
from app.crud.user_answer import user_answer as crud_user_answer
from app.crud.course import course as crud_course
from app.crud.curriculum import curriculum as crud_curriculum
from app.schemas.exam import Exam
from app.schemas.exam_attempt import ExamAttemptCreate, ExamAttemptUpdate, ExamAttempt
from app.schemas.user_answer import UserAnswerCreate, UserAnswerUpdate, UserAnswer
from app.schemas.user import UserContext
from app.core.constants import RoleEnum, QuestionTypeEnum, ExamAttemptStatusEnum
from app.services.course import course_service

class ExamAttemptService:
    def _can_start_exam_attempt(self, db: Session, current_user_context: UserContext, exam: Exam):
        if current_user_context.role.name != RoleEnum.STUDENT:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only students can start exam attempts.")

        if exam.course_id:
            course = crud_course.get(db, id=exam.course_id)
            course_service._check_course_access(current_user_context, course, allow_student_view=True)
            if not course_service._is_student_of_course(current_user_context.user, course):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You must be a student of this course to take this exam.")
        elif exam.curriculum_id:
            curriculum = crud_curriculum.get(db, id=exam.curriculum_id)
            course_service._check_course_access(current_user_context, curriculum.course, allow_student_view=True)
            if not course_service._is_student_of_course(current_user_context.user, curriculum.course):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You must be a student of this course to take this exam.")
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Exam is not associated with a course or curriculum.")

    def _can_submit_answer_or_exam(self, db: Session, current_user_context: UserContext, attempt: ExamAttempt):
        if attempt.user_id != current_user_context.user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only submit answers for your own attempts.")

        if attempt.status != ExamAttemptStatusEnum.IN_PROGRESS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot submit answers for an exam attempt that is not in progress.")

    def _can_view_exam_attempt(self, db: Session, current_user_context: UserContext, attempt: ExamAttempt):
        if attempt.user_id == current_user_context.user.id:
            return

        if current_user_context.role.name == RoleEnum.STUDENT:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only view your own exam attempts.")

        exam = crud_exam.get(db, id=attempt.exam_id)
        if not exam:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found for this attempt.")

        if exam.course_id:
            course = crud_course.get(db, id=exam.course_id)
            course_service._check_course_access(current_user_context, course, allow_student_view=True)
        elif exam.curriculum_id:
            curriculum = crud_curriculum.get(db, id=exam.curriculum_id)
            course_service._check_course_access(current_user_context, curriculum.course, allow_student_view=True)
        else:
            if current_user_context.role.name != RoleEnum.SUPER_ADMIN:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to view this exam attempt.")

    def start_exam_attempt(self, db: Session, exam_id: int, current_user_context: UserContext) -> ExamAttempt:
        exam = crud_exam.get(db, id=exam_id)
        if not exam:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found.")

        self._can_start_exam_attempt(db, current_user_context, exam)

        existing_attempts = crud_exam_attempt.get_by_user_and_exam(db, user_id=current_user_context.user.id, exam_id=exam_id)
        if not exam.allow_multiple_attempts and len(existing_attempts) > 0:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You have already attempted this exam and multiple attempts are not allowed.")

        attempt_in = ExamAttemptCreate(user_id=current_user_context.user.id, exam_id=exam_id, start_time=datetime.now())
        new_attempt = crud_exam_attempt.create(db, obj_in=attempt_in)
        return new_attempt

    def submit_answer(self, db: Session, attempt_id: int, question_id: int, answer_text: str, current_user_context: UserContext) -> UserAnswer:
        attempt = crud_exam_attempt.get(db, id=attempt_id)
        if not attempt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam attempt not found.")

        self._can_submit_answer_or_exam(db, current_user_context, attempt)

        question = crud_question.get(db, id=question_id)
        if not question:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found.")

        if question.exam_id != attempt.exam_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Question does not belong to this exam attempt.")

        user_answer_obj = crud_user_answer.get_by_attempt_and_question(db, exam_attempt_id=attempt_id, question_id=question_id)

        if user_answer_obj:
            user_answer_in = UserAnswerUpdate(answer_text=answer_text)
            updated_answer = crud_user_answer.update(db, db_obj=user_answer_obj, obj_in=user_answer_in)
        else:
            user_answer_in = UserAnswerCreate(exam_attempt_id=attempt_id, question_id=question_id, user_id=current_user_context.user.id, answer_text=answer_text)
            updated_answer = crud_user_answer.create(db, obj_in=user_answer_in)

        return updated_answer

    def submit_exam(self, db: Session, attempt_id: int, current_user_context: UserContext) -> ExamAttempt:
        attempt = crud_exam_attempt.get(db, id=attempt_id)
        if not attempt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam attempt not found.")

        self._can_submit_answer_or_exam(db, current_user_context, attempt)

        exam = crud_exam.get(db, id=attempt.exam_id)
        if not exam:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found for this attempt.")

        score, passed = self._calculate_score(db, attempt, exam)
        attempt_update = ExamAttemptUpdate(end_time=datetime.now(), score=score, passed=passed, status=ExamAttemptStatusEnum.COMPLETED)
        updated_attempt = crud_exam_attempt.update(db, db_obj=attempt, obj_in=attempt_update)

        return updated_attempt

    def _calculate_score(self, db: Session, attempt: ExamAttempt, exam: Exam) -> Any:
        total_score = 0.0
        total_possible_points = 0
        questions = crud_question.get_by_exam(db, exam_id=exam.id)
        user_answers = crud_user_answer.get_all_by_attempt(db, exam_attempt_id=attempt.id)
        user_answers_map = {ans.question_id: ans for ans in user_answers}

        for question in questions:
            total_possible_points += question.points
            user_answer = user_answers_map.get(question.id)

            if user_answer:
                is_correct = False
                if question.question_type == QuestionTypeEnum.MULTIPLE_CHOICE or question.question_type == QuestionTypeEnum.TRUE_FALSE:
                    if user_answer.answer_text == question.correct_answer:
                        is_correct = True

                user_answer.is_correct = is_correct
                if is_correct:
                    user_answer.score = question.points
                    total_score += question.points
                else:
                    user_answer.score = 0.0
                crud_user_answer.update(db, db_obj=user_answer, obj_in=user_answer)

        if total_possible_points == 0:
            final_score_percentage = 0.0
        else:
            final_score_percentage = (total_score / total_possible_points) * 100

        passed = False
        if exam.pass_percentage is not None and final_score_percentage >= exam.pass_percentage:
            passed = True

        return total_score, passed

    def get_exam_attempt(self, db: Session, attempt_id: int, current_user_context: UserContext) -> ExamAttempt:
        attempt = crud_exam_attempt.get(db, id=attempt_id)
        if not attempt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam attempt not found.")

        self._can_view_exam_attempt(db, current_user_context, attempt)

        return attempt

    def get_user_exam_attempts(self, db: Session, user_id: int, current_user_context: UserContext) -> List[ExamAttempt]:
        if user_id != current_user_context.user.id and current_user_context.role.name == RoleEnum.STUDENT:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only view your own exam attempts.")

        if current_user_context.role.name != RoleEnum.SUPER_ADMIN and user_id != current_user_context.user.id:
            pass

        attempts = crud_exam_attempt.get_all_by_user(db, user_id=user_id)
        return attempts

exam_attempt_service = ExamAttemptService()
