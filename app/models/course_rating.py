from sqlalchemy import Column, Integer, ForeignKey, DateTime, Text, Float, UniqueConstraint, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class CourseRating(Base):
    __tablename__ = "course_ratings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    rating = Column(Float, nullable=False)
    review = Column(Text, nullable=True)
    deleted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)

    __table_args__ = (
        UniqueConstraint('user_id', 'course_id', name='unique_user_course_rating'),
    )

    user = relationship("User", back_populates="course_ratings")
    course = relationship("Course", back_populates="ratings")