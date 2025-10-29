from sqlalchemy import Column, Integer, ForeignKey, DateTime, Enum as SQLEnum, func
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.constants import EnrollmentStatusEnum

class CourseEnrollment(Base):
    __tablename__ = "course_enrollments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    status = Column(SQLEnum(EnrollmentStatusEnum), default=EnrollmentStatusEnum.NOT_STARTED)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    progress_percentage = Column(Integer, default=0)
    deleted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)

    user = relationship("User", back_populates="course_enrollments")
    course = relationship("Course", back_populates="enrollments")
    lesson_progress = relationship("LessonProgress", back_populates="enrollment", cascade="all, delete-orphan")
    rewards = relationship("CourseReward", back_populates="enrollment", cascade="all, delete-orphan")  # Add this


    def calculate_progress(self):
        if not self.lesson_progress:
            return 0
        total_lessons = len(self.lesson_progress)
        if total_lessons == 0:
            return 0
        completed = sum(1 for lp in self.lesson_progress if lp.is_completed)
        return int((completed / total_lessons) * 100)