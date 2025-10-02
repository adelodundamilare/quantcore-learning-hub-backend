from sqlalchemy import Column, Integer, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from app.core.database import Base


class CourseReward(Base):
    __tablename__ = "course_rewards"

    id = Column(Integer, primary_key=True, index=True)
    enrollment_id = Column(Integer, ForeignKey("course_enrollments.id"), nullable=False)
    # reward_type = Column(String(50), nullable=False)
    # reward_title = Column(String(255), nullable=False)
    reward_description = Column(Text, nullable=True)
    points = Column(Integer, default=0)
    awarded_at = Column(DateTime, nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=True)

    enrollment = relationship("CourseEnrollment", back_populates="rewards")