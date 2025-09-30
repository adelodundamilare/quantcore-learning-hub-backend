from sqlalchemy import Column, Integer, DateTime, ForeignKey, Float, Boolean, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.core.constants import ExamAttemptStatusEnum

class ExamAttempt(Base):
    __tablename__ = "exam_attempts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=False)
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True), nullable=True)
    score = Column(Float, nullable=True)
    passed = Column(Boolean, nullable=True)
    status = Column(Enum(ExamAttemptStatusEnum), nullable=False, default=ExamAttemptStatusEnum.IN_PROGRESS)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="exam_attempts")
    exam = relationship("Exam", back_populates="attempts")
    user_answers = relationship("UserAnswer", back_populates="exam_attempt", cascade="all, delete-orphan")
