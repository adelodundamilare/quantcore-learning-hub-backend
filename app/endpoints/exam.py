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

router = APIRouter()

# Exam Endpoints
@router.post("/", response_model=APIResponse[Exam])
def create_exam(
    exam_in: ExamCreate,
    db: Session = Depends(deps.get_transactional_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    new_exam = exam_service.create_exam(db, exam_in=exam_in, current_user_context=context)
    return APIResponse(message="Exam created successfully", data=Exam.model_validate(new_exam))

@router.get("/{exam_id}", response_model=APIResponse[Exam])
def get_exam(
    exam_id: int,
    db: Session = Depends(deps.get_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    exam = exam_service.get_exam(db, exam_id=exam_id, current_user_context=context)
    return APIResponse(message="Exam retrieved successfully", data=Exam.model_validate(exam))

@router.put("/{exam_id}", response_model=APIResponse[Exam])
def update_exam(
    exam_id: int,
    exam_in: ExamUpdate,
    db: Session = Depends(deps.get_transactional_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    updated_exam = exam_service.update_exam(db, exam_id=exam_id, exam_in=exam_in, current_user_context=context)
    return APIResponse(message="Exam updated successfully", data=Exam.model_validate(updated_exam))

@router.delete("/{exam_id}", response_model=APIResponse)
def delete_exam(
    exam_id: int,
    db: Session = Depends(deps.get_transactional_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    response = exam_service.delete_exam(db, exam_id=exam_id, current_user_context=context)
    return APIResponse(message=response["message"])

# Question Endpoints
@router.post("/{exam_id}/questions/", response_model=APIResponse[Question])
def create_question(
    exam_id: int,
    question_in: QuestionCreate,
    db: Session = Depends(deps.get_transactional_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    if question_in.exam_id != exam_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Exam ID in path and body must match.")
    new_question = exam_service.create_question(db, question_in=question_in, current_user_context=context)
    return APIResponse(message="Question created successfully", data=Question.model_validate(new_question))

@router.get("/{exam_id}/questions/{question_id}", response_model=APIResponse[Question])
def get_question(
    exam_id: int,
    question_id: int,
    db: Session = Depends(deps.get_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    question = exam_service.get_question(db, question_id=question_id, current_user_context=context)
    if question.exam_id != exam_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Question does not belong to the specified exam.")
    return APIResponse(message="Question retrieved successfully", data=Question.model_validate(question))

@router.put("/{exam_id}/questions/{question_id}", response_model=APIResponse[Question])
def update_question(
    exam_id: int,
    question_id: int,
    question_in: QuestionUpdate,
    db: Session = Depends(deps.get_transactional_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    question = exam_service.get_question(db, question_id=question_id, current_user_context=context)
    if question.exam_id != exam_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Question does not belong to the specified exam.")
    updated_question = exam_service.update_question(db, question_id=question_id, question_in=question_in, current_user_context=context)
    return APIResponse(message="Question updated successfully", data=Question.model_validate(updated_question))

@router.delete("/{exam_id}/questions/{question_id}", response_model=APIResponse)
def delete_question(
    exam_id: int,
    question_id: int,
    db: Session = Depends(deps.get_transactional_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    question = exam_service.get_question(db, question_id=question_id, current_user_context=context)
    if question.exam_id != exam_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Question does not belong to the specified exam.")
    response = exam_service.delete_question(db, question_id=question_id, current_user_context=context)
    return APIResponse(message=response["message"])

# Exam Attempt Endpoints
@router.post("/{exam_id}/attempts/", response_model=APIResponse[ExamAttempt])
def start_exam_attempt(
    exam_id: int,
    db: Session = Depends(deps.get_transactional_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    new_attempt = exam_attempt_service.start_exam_attempt(db, exam_id=exam_id, current_user_context=context)
    return APIResponse(message="Exam attempt started successfully", data=ExamAttempt.model_validate(new_attempt))

@router.post("/{exam_id}/attempts/{attempt_id}/submit_answer", response_model=APIResponse[UserAnswer])
def submit_answer(
    exam_id: int,
    attempt_id: int,
    user_answer_in: UserAnswerCreate,
    db: Session = Depends(deps.get_transactional_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    if user_answer_in.exam_attempt_id != attempt_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Attempt ID in path and body must match.")
    # Further validation to ensure question_id belongs to exam_id and attempt_id
    updated_answer = exam_attempt_service.submit_answer(db, attempt_id=attempt_id, question_id=user_answer_in.question_id, answer_text=user_answer_in.answer_text, current_user_context=context)
    return APIResponse(message="Answer submitted successfully", data=UserAnswer.model_validate(updated_answer))

@router.post("/{exam_id}/attempts/{attempt_id}/submit_exam", response_model=APIResponse[ExamAttempt])
def submit_exam(
    exam_id: int,
    attempt_id: int,
    db: Session = Depends(deps.get_transactional_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    updated_attempt = exam_attempt_service.submit_exam(db, attempt_id=attempt_id, current_user_context=context)
    return APIResponse(message="Exam submitted successfully", data=ExamAttempt.model_validate(updated_attempt))

@router.get("/{exam_id}/attempts/{attempt_id}/results", response_model=APIResponse[ExamAttempt])
def get_exam_results(
    exam_id: int,
    attempt_id: int,
    db: Session = Depends(deps.get_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    attempt = exam_attempt_service.get_exam_attempt(db, attempt_id=attempt_id, current_user_context=context)
    if attempt.exam_id != exam_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Attempt does not belong to the specified exam.")
    return APIResponse(message="Exam results retrieved successfully", data=ExamAttempt.model_validate(attempt))

@router.get("/users/{user_id}/exam_attempts", response_model=APIResponse[List[ExamAttempt]])
def get_user_exam_attempts(
    user_id: int,
    db: Session = Depends(deps.get_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    attempts = exam_attempt_service.get_user_exam_attempts(db, user_id=user_id, current_user_context=context)
    return APIResponse(message="User exam attempts retrieved successfully", data=[ExamAttempt.model_validate(a) for a in attempts])
