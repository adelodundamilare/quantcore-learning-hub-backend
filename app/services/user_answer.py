from typing import List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.crud.user_answer import user_answer as crud_user_answer
from app.crud.exam_attempt import exam_attempt as crud_exam_attempt
from app.schemas.user_answer import  UserAnswer
from app.schemas.user import UserContext
from app.core.constants import RoleEnum
from app.services.exam_attempt import exam_attempt_service

class UserAnswerService:
    def _can_view_user_answer(self, db: Session, current_user_context: UserContext, user_answer: UserAnswer):
        if user_answer.user_id == current_user_context.user.id:
            return

        if current_user_context.role.name == RoleEnum.STUDENT:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only view your own answers.")

        attempt = crud_exam_attempt.get(db, id=user_answer.exam_attempt_id)
        if not attempt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam attempt not found for this answer.")
        exam_attempt_service._can_view_exam_attempt(db, current_user_context, attempt)

    def get_user_answer(self, db: Session, user_answer_id: int, current_user_context: UserContext) -> UserAnswer:
        user_answer = crud_user_answer.get(db, id=user_answer_id)
        if not user_answer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User answer not found.")

        self._can_view_user_answer(db, current_user_context, user_answer)

        return user_answer

    def get_answers_for_attempt(self, db: Session, exam_attempt_id: int, current_user_context: UserContext) -> List[UserAnswer]:
        attempt = crud_exam_attempt.get(db, id=exam_attempt_id)
        if not attempt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam attempt not found.")

        exam_attempt_service._can_view_exam_attempt(db, current_user_context, attempt)

        return crud_user_answer.get_all_by_attempt(db, exam_attempt_id=exam_attempt_id)

user_answer_service = UserAnswerService()
