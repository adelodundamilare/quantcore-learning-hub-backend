from typing import List, Optional
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session
from app.core.constants import CourseLevelEnum

from app.schemas.response import APIResponse
from app.utils import deps
from app.schemas.exam import Exam, ExamCreate, ExamUpdate
from app.schemas.question import Question, QuestionCreate, QuestionUpdate
from app.schemas.exam_attempt import ExamAttempt, ExamAttemptDetails
from app.schemas.user_answer import UserAnswer, UserAnswerCreate
from app.services.exam import exam_service
from app.services.exam_attempt import exam_attempt_service
from app.schemas.user import UserContext
from app.schemas.report import StudentExamStats
from app.services.report import report_service
from app.core.decorators import cache_endpoint
from app.core.cache import cache

router = APIRouter()

@router.post("/", response_model=APIResponse[Exam], status_code=status.HTTP_201_CREATED)
async def create_exam(
    *,
    db: Session = Depends(deps.get_transactional_db),
    exam_in: ExamCreate,
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    new_exam = await exam_service.create_exam(db, exam_in=exam_in, current_user_context=context)
    await cache.invalidate_user_cache(context.user.id)
    return APIResponse(message="Exam created successfully", data=Exam.model_validate(new_exam))


@router.get("/", response_model=APIResponse[List[Exam]])
@cache_endpoint(ttl=600)
async def get_all_exams(
    db: Session = Depends(deps.get_db),
    context: UserContext = Depends(deps.get_current_user_with_context),
    skip: int = 0,
    limit: int = 100,
    level: Optional[CourseLevelEnum] = Query(None)
):
    exams = exam_service.get_all_exams(db, current_user_context=context, skip=skip, limit=limit, level=level)
    return APIResponse(message="Exams retrieved successfully", data=[Exam.model_validate(e) for e in exams])


@router.get("/{exam_id}", response_model=APIResponse[Exam])
@cache_endpoint(ttl=600)
async def get_exam(
    *,
    db: Session = Depends(deps.get_db),
    exam_id: int,
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    exam = exam_service.get_exam(db, exam_id=exam_id, current_user_context=context)
    return APIResponse(message="Exam retrieved successfully", data=Exam.model_validate(exam))


@router.put("/{exam_id}", response_model=APIResponse[Exam])
async def update_exam(
    *,
    db: Session = Depends(deps.get_transactional_db),
    exam_id: int,
    exam_in: ExamUpdate,
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    updated_exam = await exam_service.update_exam(db, exam_id=exam_id, exam_in=exam_in, current_user_context=context)
    await cache.invalidate_user_cache(context.user.id)
    return APIResponse(message="Exam updated successfully", data=Exam.model_validate(updated_exam))


@router.delete("/{exam_id}", response_model=APIResponse[Exam])
async def delete_exam(
    *,
    db: Session = Depends(deps.get_transactional_db),
    exam_id: int,
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    deleted_exam = await exam_service.delete_exam(db, exam_id=exam_id, current_user_context=context)
    await cache.invalidate_user_cache(context.user.id)
    return APIResponse(message="Exam deleted successfully", data=Exam.model_validate(deleted_exam))


@router.get("/{exam_id}/questions", response_model=APIResponse[List[Question]])
@cache_endpoint(ttl=600)
async def get_exam_questions(
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


@router.post("/{exam_id}/questions", response_model=APIResponse[List[Question]], status_code=status.HTTP_201_CREATED)
async def create_questions(
    *,
    db: Session = Depends(deps.get_transactional_db),
    exam_id: int,
    questions_in: List[QuestionCreate],
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    for question in questions_in:
        if question.exam_id != exam_id:
            question.exam_id = exam_id

    new_questions = exam_service.create_questions(db, questions_in=questions_in, current_user_context=context)
    await cache.invalidate_user_cache(context.user.id)
    return APIResponse(message="Questions created successfully", data=[Question.model_validate(q) for q in new_questions])


@router.get("/questions/{question_id}", response_model=APIResponse[Question])
@cache_endpoint(ttl=600)
async def get_question(
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
async def update_question(
    *,
    db: Session = Depends(deps.get_transactional_db),
    question_id: int,
    question_in: QuestionUpdate,
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    updated_question = exam_service.update_question(db, question_id=question_id, question_in=question_in, current_user_context=context)
    await cache.invalidate_user_cache(context.user.id)
    return APIResponse(message="Question updated successfully", data=Question.model_validate(updated_question))


@router.delete("/questions/{question_id}", response_model=APIResponse[Question])
async def delete_question(
    *,
    db: Session = Depends(deps.get_transactional_db),
    question_id: int,
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    deleted_question = exam_service.delete_question(db, question_id=question_id, current_user_context=context)
    await cache.invalidate_user_cache(context.user.id)
    return APIResponse(message="Question deleted successfully", data=Question.model_validate(deleted_question))

# Exam Attempt Endpoints
@router.post("/{exam_id}/attempts", response_model=APIResponse[ExamAttempt], status_code=status.HTTP_201_CREATED)
async def start_exam_attempt(
    *,
    db: Session = Depends(deps.get_transactional_db),
    exam_id: int,
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    new_attempt = exam_attempt_service.start_exam_attempt(db, exam_id=exam_id, current_user_context=context)
    await cache.invalidate_user_cache(context.user.id)
    return APIResponse(message="Exam attempt started successfully", data=ExamAttempt.model_validate(new_attempt))


@router.post("/attempts/{attempt_id}/answers", response_model=APIResponse[UserAnswer])
async def submit_answer(
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
    await cache.invalidate_user_cache(context.user.id)
    return APIResponse(message="Answer submitted successfully", data=UserAnswer.model_validate(user_answer))


@router.post("/attempts/{attempt_id}/answers/bulk", response_model=APIResponse[List[UserAnswer]])
async def submit_bulk_answers(
    *,
    db: Session = Depends(deps.get_transactional_db),
    attempt_id: int,
    answers_in: List[UserAnswerCreate],
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    user_answers = exam_attempt_service.submit_bulk_answers(
        db,
        attempt_id=attempt_id,
        answers_in=answers_in,
        current_user_context=context
    )
    await cache.invalidate_user_cache(context.user.id)
    return APIResponse(message="Answers submitted successfully", data=[UserAnswer.model_validate(ua) for ua in user_answers])


@router.post("/attempts/{attempt_id}/submit", response_model=APIResponse[ExamAttemptDetails])
async def submit_exam(
    *,
    db: Session = Depends(deps.get_transactional_db),
    attempt_id: int,
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    completed_attempt = await exam_attempt_service.submit_exam(db, attempt_id=attempt_id, current_user_context=context)
    await cache.invalidate_user_cache(context.user.id)
    return APIResponse(message="Exam submitted successfully", data=completed_attempt)


@router.get("/attempts/{attempt_id}", response_model=APIResponse[ExamAttemptDetails])
@cache_endpoint(ttl=300)
async def get_exam_attempt(
    *,
    db: Session = Depends(deps.get_db),
    attempt_id: int,
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    attempt = exam_attempt_service.get_exam_attempt(db, attempt_id=attempt_id, current_user_context=context)
    return APIResponse(message="Exam attempt retrieved successfully", data=attempt)


@router.get("/users/{user_id}/attempts", response_model=APIResponse[List[ExamAttempt]])
@cache_endpoint(ttl=300)
async def get_user_exam_attempts(
    *,
    db: Session = Depends(deps.get_db),
    user_id: int,
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    attempts = exam_attempt_service.get_user_exam_attempts(db, user_id=user_id, current_user_context=context)
    return APIResponse(message="User exam attempts retrieved successfully", data=[ExamAttempt.model_validate(a) for a in attempts])


@router.get("/{exam_id}/attempts", response_model=APIResponse[List[ExamAttempt]])
@cache_endpoint(ttl=600)
async def get_exam_attempts(
    *,
    db: Session = Depends(deps.get_db),
    exam_id: int,
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    attempts = exam_attempt_service.get_exam_attempts_by_exam(db, exam_id=exam_id, current_user_context=context)
    return APIResponse(message="Exam attempts retrieved successfully", data=[ExamAttempt.model_validate(a) for a in attempts])

@router.get("/student/my/stats", response_model=APIResponse[StudentExamStats], status_code=status.HTTP_200_OK)
@cache_endpoint(ttl=300)
async def get_student_exam_statistics(
    *,
    db: Session = Depends(deps.get_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    stats = report_service.get_student_exam_stats(db, current_user_context=context)
    return APIResponse(message="Student exam stats retrieved successfully", data=stats)