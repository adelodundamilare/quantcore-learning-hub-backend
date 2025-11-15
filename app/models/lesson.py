from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.core.constants import LessonTypeEnum

class Lesson(Base):
    __tablename__ = "lessons"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    content = Column(String, nullable=True)
    lesson_type = Column(Enum(LessonTypeEnum), nullable=False, default=LessonTypeEnum.TEXT)
    duration = Column(Integer, nullable=False, default=0) # Duration in minutes
    order = Column(Integer, nullable=False, default=0)
    curriculum_id = Column(Integer, ForeignKey("curriculums.id"), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    curriculum = relationship("Curriculum", back_populates="lessons")
    progress_records = relationship("LessonProgress", primaryjoin="and_(Lesson.id == LessonProgress.lesson_id, LessonProgress.deleted_at == None)", back_populates="lesson")
