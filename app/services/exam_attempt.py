from typing import Tuple, List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime

from app.core.database import SessionLocal
from app.crud.exam import exam as crud_exam
from app.crud.question import question as crud_question
from app.crud.exam_attempt import exam_attempt as crud_exam_attempt
from app.crud.user_answer import user_answer as crud_user_answer
from app.crud.course import course as crud_course
from app.crud.curriculum import curriculum as crud_curriculum
from app.schemas.exam import Exam
from app.schemas.exam_attempt import ExamAttemptCreate, ExamAttemptDetails, ExamAttemptUpdate, ExamAttempt
from app.schemas.question import QuestionWithUserAnswer
from app.schemas.user_answer import UserAnswerCreate, UserAnswerUpdate, UserAnswer
from app.schemas.user import UserContext
from app.core.constants import EnrollmentStatusEnum, ExamAttemptStatusEnum
from app.utils.permission import PermissionHelper as permission_helper
from app.utils.events import event_bus
from app.crud.course_enrollment import course_enrollment as enrollment_crud
from app.services.reward_rating import reward_rating_service


class ExamAttemptService:

    def _get_course_from_exam(self, db: Session, exam: Exam):
        if exam.course_id:
            course = crud_course.get(db, id=exam.course_id)
            if not course:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")
            return course
        elif exam.curriculum_id:
            curriculum = crud_curriculum.get(db, id=exam.curriculum_id)
            if not curriculum:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Curriculum not found.")
            return curriculum.course
        return None

    def _require_student_enrollment_in_exam(self, db: Session, current_user_context: UserContext, exam: Exam):
        if not permission_helper.is_student(current_user_context):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only students can start exam attempts."
            )

        course = self._get_course_from_exam(db, exam)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Exam is not associated with a course or curriculum."
            )

        permission_helper.require_course_view_permission(current_user_context, course)

        if not permission_helper.is_student_of_course(current_user_context.user.id, course):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You must be a student of this course to take this exam."
            )

    def _require_attempt_ownership_and_in_progress(self, current_user_context: UserContext, attempt: ExamAttempt):
        if attempt.user_id != current_user_context.user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only submit answers for your own attempts."
            )

        if attempt.status != ExamAttemptStatusEnum.IN_PROGRESS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot submit answers for an exam attempt that is not in progress."
            )

    def _require_attempt_view_permission(self, db: Session, current_user_context: UserContext, attempt: ExamAttempt):
        if attempt.user_id == current_user_context.user.id:
            return

        if permission_helper.is_student(current_user_context):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own exam attempts."
            )

        exam = crud_exam.get(db, id=attempt.exam_id)
        if not exam:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found for this attempt.")

        course = self._get_course_from_exam(db, exam)
        if not course:
            if not permission_helper.is_super_admin(current_user_context):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have permission to view this exam attempt."
                )
            return

        permission_helper.require_course_view_permission(current_user_context, course)

    def _validate_question_belongs_to_exam(self, question, attempt):
        if question.exam_id != attempt.exam_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Question does not belong to this exam attempt."
            )

    def _calculate_score(self, db: Session, attempt: ExamAttempt, exam: Exam) -> Tuple[float, bool]:
        total_score = 0.0
        total_possible_points = 0

        questions = crud_question.get_by_exam(db, exam_id=exam.id)
        user_answers = crud_user_answer.get_all_by_attempt(db, exam_attempt_id=attempt.id)
        user_answers_map = {ans.question_id: ans for ans in user_answers}

        for question in questions:
            total_possible_points += question.points
            user_answer = user_answers_map.get(question.id)

            if user_answer:
                try:
                    user_answer_int = int(user_answer.answer_text)
                    correct_answer_int = int(question.correct_answer)
                    is_correct = user_answer_int == correct_answer_int
                except (ValueError, TypeError):
                    is_correct = False
                    correct_answer_int = None

                score = question.points if is_correct else 0.0
                total_score += score

                update_data = UserAnswerUpdate(
                    is_correct=is_correct,
                    score=score)

                crud_user_answer.update(db, db_obj=user_answer, obj_in=update_data)

        final_score_percentage = (total_score / total_possible_points * 100) if total_possible_points > 0 else 0.0
        passed = exam.pass_percentage is not None and final_score_percentage >= exam.pass_percentage

        return total_score, passed

    def start_exam_attempt(self, db: Session, exam_id: int, current_user_context: UserContext) -> ExamAttempt:
        exam = crud_exam.get(db, id=exam_id)
        if not exam:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found.")

        self._require_student_enrollment_in_exam(db, current_user_context, exam)

        existing_attempts = crud_exam_attempt.get_by_user_and_exam(
            db,
            user_id=current_user_context.user.id,
            exam_id=exam_id
        )

        if not exam.allow_multiple_attempts and existing_attempts:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You have already attempted this exam and multiple attempts are not allowed."
            )

        attempt_in = ExamAttemptCreate(
            user_id=current_user_context.user.id,
            exam_id=exam_id,
            start_time=datetime.now()
        )
        new_attempt = crud_exam_attempt.create(db, obj_in=attempt_in)
        db.flush()

        return new_attempt

    def submit_answer(self, db: Session, attempt_id: int, question_id: int,
                     answer_text: str, current_user_context: UserContext) -> UserAnswer:
        attempt = crud_exam_attempt.get(db, id=attempt_id)
        if not attempt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam attempt not found.")

        self._require_attempt_ownership_and_in_progress(current_user_context, attempt)

        question = crud_question.get(db, id=question_id)
        if not question:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found.")

        self._validate_question_belongs_to_exam(question, attempt)

        existing_answer = crud_user_answer.get_by_attempt_and_question(
            db,
            exam_attempt_id=attempt_id,
            question_id=question_id
        )

        if existing_answer:
            answer_in = UserAnswerUpdate(answer_text=answer_text)
            updated_answer = crud_user_answer.update(db, db_obj=existing_answer, obj_in=answer_in)
        else:
            answer_in = UserAnswerCreate(
                user_id=current_user_context.user.id,
                exam_attempt_id=attempt_id,
                question_id=question_id,
                answer_text=answer_text
            )
            updated_answer = crud_user_answer.create(db, obj_in=answer_in)

        return updated_answer

    def submit_bulk_answers(self, db: Session, attempt_id: int, answers_in: List[UserAnswerCreate], current_user_context: UserContext) -> List[UserAnswer]:
        if not answers_in:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No answers provided.")

        question_ids = [ans.question_id for ans in answers_in]
        if len(question_ids) != len(set(question_ids)):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Duplicate question_ids found in submission.")

        attempt = crud_exam_attempt.get(db, id=attempt_id)
        if not attempt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam attempt not found.")

        self._require_attempt_ownership_and_in_progress(current_user_context, attempt)

        exam_questions = {q.id for q in crud_question.get_by_exam(db, exam_id=attempt.exam_id)}
        invalid_questions = [ans.question_id for ans in answers_in if ans.question_id not in exam_questions]

        if invalid_questions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid question_id(s): {invalid_questions}. All questions must belong to the exam."
            )

        existing_answers = {ans.question_id: ans for ans in crud_user_answer.get_all_by_attempt(db, exam_attempt_id=attempt_id)}
        processed_answers = []

        for answer_in in answers_in:
            if answer_in.question_id in existing_answers:
                existing_answer = existing_answers[answer_in.question_id]
                update_data = UserAnswerUpdate(answer_text=answer_in.answer_text)
                updated_answer = crud_user_answer.update(db, db_obj=existing_answer, obj_in=update_data)
                processed_answers.append(updated_answer)
            else:
                create_data = UserAnswerCreate(
                    user_id=current_user_context.user.id,
                    exam_attempt_id=attempt_id,
                    question_id=answer_in.question_id,
                    answer_text=answer_in.answer_text
                )
                new_answer = crud_user_answer.create(db, obj_in=create_data)
                processed_answers.append(new_answer)

        return processed_answers

    async def submit_exam(self, db: Session, attempt_id: int, current_user_context: UserContext) -> ExamAttemptDetails:
        attempt = crud_exam_attempt.get(db, id=attempt_id)
        if not attempt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam attempt not found.")

        self._require_attempt_ownership_and_in_progress(current_user_context, attempt)

        exam = crud_exam.get(db, id=attempt.exam_id)
        if not exam:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found for this attempt.")

        score, passed = self._calculate_score(db, attempt, exam)

        attempt_update = ExamAttemptUpdate(
            end_time=datetime.now(),
            score=score,
            passed=passed,
            status=ExamAttemptStatusEnum.COMPLETED
        )
        updated_attempt = crud_exam_attempt.update(db, db_obj=attempt, obj_in=attempt_update)

        questions = crud_question.get_by_exam(db, exam_id=exam.id)
        user_answers = crud_user_answer.get_all_by_attempt(db, exam_attempt_id=updated_attempt.id)
        user_answers_map = {ans.question_id: ans for ans in user_answers}

        questions_with_answers = []
        for question in questions:
            user_answer = user_answers_map.get(question.id)
            questions_with_answers.append(QuestionWithUserAnswer(user_answer=user_answer, **question.__dict__))

        result = ExamAttemptDetails(exam=exam, questions=questions_with_answers)

        if passed and exam.course_id:
            await event_bus.publish("course_completed", {
                "student_id": current_user_context.user.id,
                "course_id": exam.course_id,
                "school_id": exam.course.school_id if exam.course else None
            })

        return result

    def get_exam_attempt(self, db: Session, attempt_id: int, current_user_context: UserContext) -> ExamAttemptDetails:
        attempt = crud_exam_attempt.get(db, id=attempt_id)
        if not attempt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam attempt not found.")

        self._require_attempt_view_permission(db, current_user_context, attempt)

        exam = crud_exam.get(db, id=attempt.exam_id)
        if not exam:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found for this attempt.")

        questions = crud_question.get_by_exam(db, exam_id=exam.id)
        user_answers = crud_user_answer.get_all_by_attempt(db, exam_attempt_id=attempt.id)
        user_answers_map = {ans.question_id: ans for ans in user_answers}

        questions_with_answers = []
        for question in questions:
            user_answer = user_answers_map.get(question.id)
            questions_with_answers.append(QuestionWithUserAnswer(user_answer=user_answer, **question.__dict__))

        return ExamAttemptDetails(exam=exam, questions=questions_with_answers)

    def get_user_exam_attempts(self, db: Session, user_id: int, current_user_context: UserContext) -> List[ExamAttempt]:
        if user_id != current_user_context.user.id:
            if permission_helper.is_student(current_user_context):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only view your own exam attempts."
                )

        attempts = crud_exam_attempt.get_all_by_user(db, user_id=user_id)

        if not permission_helper.is_super_admin(current_user_context) and user_id != current_user_context.user.id:
            filtered_attempts = []
            for attempt in attempts:
                exam = crud_exam.get(db, id=attempt.exam_id)
                if exam:
                    course = self._get_course_from_exam(db, exam)
                    if course and permission_helper.can_view_course(current_user_context, course):
                        filtered_attempts.append(attempt)
            return filtered_attempts

        return attempts

    def get_exam_attempts_by_exam(self, db: Session, exam_id: int,
                                 current_user_context: UserContext) -> List[ExamAttempt]:
        exam = crud_exam.get(db, id=exam_id)
        if not exam:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found.")

        course = self._get_course_from_exam(db, exam)
        if course:
            permission_helper.require_course_view_permission(current_user_context, course)
        elif not permission_helper.is_super_admin(current_user_context):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view attempts for this exam."
            )

        if permission_helper.is_student(current_user_context):
            return crud_exam_attempt.get_by_user_and_exam(
                db,
                user_id=current_user_context.user.id,
                exam_id=exam_id
            )

        return crud_exam_attempt.get_all_by_exam(db, exam_id=exam_id)

    async def _process_course_completion_async(self, course_id: int, user_id: int):

        db = SessionLocal()
        try:
            enrollment = enrollment_crud.get_by_user_and_course(db, user_id=user_id, course_id=course_id)
            if not enrollment or enrollment.status == EnrollmentStatusEnum.COMPLETED:
                return

            enrollment_crud.update_status(db, enrollment.id, EnrollmentStatusEnum.COMPLETED)

            mock_admin_context = UserContext(
                user_id=1,
                user=None,
                school_id=enrollment.course.school_id,
                role_name="school_admin"
            )

            try:
                await reward_rating_service.award_completion_reward(
                    db, enrollment_id=enrollment.id, current_user_context=mock_admin_context
                )
            except Exception:
                pass

        finally:
            db.close()


exam_attempt_service = ExamAttemptService()
