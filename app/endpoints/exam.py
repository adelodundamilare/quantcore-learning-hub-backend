from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.schemas.response import APIResponse
from app.utils import deps
from app.schemas.exam import Exam, ExamCreate, ExamUpdate
from app.schemas.question import Question, QuestionCreate, QuestionUpdate
from app.schemas.exam_attempt import ExamAttempt
from app.schemas.user_answer import UserAnswer, UserAnswerCreate
from app.services.exam import exam_service
from app.services.exam_attempt import exam_attempt_service
from app.schemas.user import UserContext
from typing import List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

router = APIRouter()

@router.post("/", response_model=APIResponse[Exam], status_code=status.HTTP_201_CREATED)
def create_exam(
    *,
    db: Session = Depends(deps.get_transactional_db),
    exam_in: ExamCreate,
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    new_exam = exam_service.create_exam(db, exam_in=exam_in, current_user_context=context)
    return APIResponse(message="Exam created successfully", data=Exam.model_validate(new_exam))


@router.get("/", response_model=APIResponse[List[Exam]])
def get_all_exams(
    db: Session = Depends(deps.get_db),
    context: UserContext = Depends(deps.get_current_user_with_context),
    skip: int = 0,
    limit: int = 100
):
    exams = exam_service.get_all_exams(db, current_user_context=context, skip=skip, limit=limit)
    return APIResponse(message="Exams retrieved successfully", data=[Exam.model_validate(e) for e in exams])


@router.get("/{exam_id}", response_model=APIResponse[Exam])
def get_exam(
    *,
    db: Session = Depends(deps.get_db),
    exam_id: int,
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    exam = exam_service.get_exam(db, exam_id=exam_id, current_user_context=context)
    return APIResponse(message="Exam retrieved successfully", data=Exam.model_validate(exam))


@router.put("/{exam_id}", response_model=APIResponse[Exam])
def update_exam(
    *,
    db: Session = Depends(deps.get_transactional_db),
    exam_id: int,
    exam_in: ExamUpdate,
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    updated_exam = exam_service.update_exam(db, exam_id=exam_id, exam_in=exam_in, current_user_context=context)
    return APIResponse(message="Exam updated successfully", data=Exam.model_validate(updated_exam))


@router.delete("/{exam_id}", response_model=APIResponse[Exam])
def delete_exam(
    *,
    db: Session = Depends(deps.get_transactional_db),
    exam_id: int,
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    deleted_exam = exam_service.delete_exam(db, exam_id=exam_id, current_user_context=context)
    return APIResponse(message="Exam deleted successfully", data=Exam.model_validate(deleted_exam))


@router.get("/{exam_id}/questions", response_model=APIResponse[List[Question]])
def get_exam_questions(
    *,
    db: Session = Depends(deps.get_db),
    exam_id: int,
    context: UserContext = Depends(deps.get_current_user_with_context),
    include_correct_answers: bool = Query(False)
):
    questions = exam_service.get_exam_questions(
        db,
        exam_id=exam_id,
        current_user_context=context,
        include_correct_answers=include_correct_answers
    )
    return APIResponse(message="Exam questions retrieved successfully", data=[Question.model_validate(q) for q in questions])


@router.post("/{exam_id}/questions", response_model=APIResponse[Question], status_code=status.HTTP_201_CREATED)
def create_question(
    *,
    db: Session = Depends(deps.get_transactional_db),
    exam_id: int,
    question_in: QuestionCreate,
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    if question_in.exam_id != exam_id:
        question_in.exam_id = exam_id

    new_question = exam_service.create_question(db, question_in=question_in, current_user_context=context)
    return APIResponse(message="Question created successfully", data=Question.model_validate(new_question))


@router.get("/questions/{question_id}", response_model=APIResponse[Question])
def get_question(
    *,
    db: Session = Depends(deps.get_db),
    question_id: int,
    context: UserContext = Depends(deps.get_current_user_with_context),
    include_correct_answer: bool = Query(False)
):
    question = exam_service.get_question(
        db,
        question_id=question_id,
        current_user_context=context,
        include_correct_answer=include_correct_answer
    )
    return APIResponse(message="Question retrieved successfully", data=Question.model_validate(question))


@router.put("/questions/{question_id}", response_model=APIResponse[Question])
def update_question(
    *,
    db: Session = Depends(deps.get_transactional_db),
    question_id: int,
    question_in: QuestionUpdate,
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    updated_question = exam_service.update_question(db, question_id=question_id, question_in=question_in, current_user_context=context)
    return APIResponse(message="Question updated successfully", data=Question.model_validate(updated_question))


@router.delete("/questions/{question_id}", response_model=APIResponse[Question])
def delete_question(
    *,
    db: Session = Depends(deps.get_transactional_db),
    question_id: int,
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    deleted_question = exam_service.delete_question(db, question_id=question_id, current_user_context=context)
    return APIResponse(message="Question deleted successfully", data=Question.model_validate(deleted_question))

# Exam Attempt Endpoints
@router.post("/exams/{exam_id}/attempts", response_model=APIResponse[ExamAttempt], status_code=status.HTTP_201_CREATED)
def start_exam_attempt(
    *,
    db: Session = Depends(deps.get_transactional_db),
    exam_id: int,
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    new_attempt = exam_attempt_service.start_exam_attempt(db, exam_id=exam_id, current_user_context=context)
    return APIResponse(message="Exam attempt started successfully", data=ExamAttempt.model_validate(new_attempt))


@router.post("/attempts/{attempt_id}/answers", response_model=APIResponse[UserAnswer])
def submit_answer(
    *,
    db: Session = Depends(deps.get_transactional_db),
    attempt_id: int,
    answer_in: UserAnswerCreate,
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    user_answer = exam_attempt_service.submit_answer(
        db,
        attempt_id=attempt_id,
        question_id=answer_in.question_id,
        answer_text=answer_in.answer_text,
        current_user_context=context
    )
    return APIResponse(message="Answer submitted successfully", data=UserAnswer.model_validate(user_answer))


@router.post("/attempts/{attempt_id}/submit", response_model=APIResponse[ExamAttempt])
def submit_exam(
    *,
    db: Session = Depends(deps.get_transactional_db),
    attempt_id: int,
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    completed_attempt = exam_attempt_service.submit_exam(db, attempt_id=attempt_id, current_user_context=context)
    return APIResponse(message="Exam submitted successfully", data=ExamAttempt.model_validate(completed_attempt))


@router.get("/attempts/{attempt_id}", response_model=APIResponse[ExamAttempt])
def get_exam_attempt(
    *,
    db: Session = Depends(deps.get_db),
    attempt_id: int,
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    attempt = exam_attempt_service.get_exam_attempt(db, attempt_id=attempt_id, current_user_context=context)
    return APIResponse(message="Exam attempt retrieved successfully", data=ExamAttempt.model_validate(attempt))


@router.get("/users/{user_id}/attempts", response_model=APIResponse[List[ExamAttempt]])
def get_user_exam_attempts(
    *,
    db: Session = Depends(deps.get_db),
    user_id: int,
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    attempts = exam_attempt_service.get_user_exam_attempts(db, user_id=user_id, current_user_context=context)
    return APIResponse(message="User exam attempts retrieved successfully", data=[ExamAttempt.model_validate(a) for a in attempts])


@router.get("/exams/{exam_id}/attempts", response_model=APIResponse[List[ExamAttempt]])
def get_exam_attempts(
    *,
    db: Session = Depends(deps.get_db),
    exam_id: int,
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    attempts = exam_attempt_service.get_exam_attempts_by_exam(db, exam_id=exam_id, current_user_context=context)
    return APIResponse(message="Exam attempts retrieved successfully", data=[ExamAttempt.model_validate(a) for a in attempts])