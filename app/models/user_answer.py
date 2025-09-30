from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class UserAnswer(Base):
    __tablename__ = "user_answers"

    id = Column(Integer, primary_key=True, index=True)
    exam_attempt_id = Column(Integer, ForeignKey("exam_attempts.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    answer_text = Column(Integer, nullable=True) # Stores the index of the user's chosen option
    is_correct = Column(Boolean, nullable=True) # For auto-graded questions
    score = Column(Float, nullable=True) # For manually graded questions or partial scores
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    exam_attempt = relationship("ExamAttempt", back_populates="user_answers")
    question = relationship("Question", back_populates="user_answers")
    user = relationship("User", back_populates="user_answers")
