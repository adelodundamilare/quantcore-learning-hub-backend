from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.core.constants import CourseLevelEnum

class Exam(Base):
    __tablename__ = "exams"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    description = Column(String, nullable=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)
    curriculum_id = Column(Integer, ForeignKey("curriculums.id"), nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    pass_percentage = Column(Float, nullable=True)
    is_active = Column(Boolean, default=True)
    allow_multiple_attempts = Column(Boolean, default=False)
    show_results_immediately = Column(Boolean, default=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    course = relationship("Course", back_populates="exams")
    curriculum = relationship("Curriculum", back_populates="exams")
    questions = relationship("Question", back_populates="exam", cascade="all, delete-orphan")
    attempts = relationship("ExamAttempt", back_populates="exam", cascade="all, delete-orphan")

    @property
    def level(self):
        if self.course:
            return self.course.level
        if self.curriculum and self.curriculum.course:
            return self.curriculum.course.level
        return None
