from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Curriculum(Base):
    __tablename__ = "curriculums"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    description = Column(String, nullable=True)
    order = Column(Integer, nullable=False, default=0)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    course = relationship("Course", back_populates="curriculums")
    lessons = relationship("Lesson", primaryjoin="and_(Curriculum.id == Lesson.curriculum_id, Lesson.deleted_at == None)", back_populates="curriculum", cascade="all, delete-orphan")
    exams = relationship("Exam", primaryjoin="and_(Curriculum.id == Exam.curriculum_id, Exam.deleted_at == None)", back_populates="curriculum", cascade="all, delete-orphan")
