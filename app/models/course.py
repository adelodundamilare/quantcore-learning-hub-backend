from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Table, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.core.constants import CourseLevelEnum

course_teachers_association = Table(
    "course_teachers_association",
    Base.metadata,
    Column("course_id", Integer, ForeignKey("courses.id"), primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
)

course_students_association = Table(
    "course_students_association",
    Base.metadata,
    Column("course_id", Integer, ForeignKey("courses.id"), primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
)

class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    description = Column(String, nullable=True)
    thumbnail = Column(String, nullable=True)
    level = Column(Enum(CourseLevelEnum), nullable=False, default=CourseLevelEnum.BEGINNER)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    school = relationship("School", back_populates="courses")
    teachers = relationship("User", secondary=course_teachers_association, back_populates="teaching_courses")
    students = relationship("User", secondary=course_students_association, back_populates="enrolled_courses")
    curriculums = relationship("Curriculum", back_populates="course", cascade="all, delete-orphan")
    exams = relationship("Exam", back_populates="course", cascade="all, delete-orphan")
    enrollments = relationship("CourseEnrollment", back_populates="course")
    ratings = relationship("CourseRating", back_populates="course")

    @property
    def average_rating(self):
        if not self.ratings:
            return 0.0
        total = sum(r.rating for r in self.ratings if not r.deleted_at)
        active_ratings = [r for r in self.ratings if not r.deleted_at]
        return round(total / len(active_ratings), 2) if active_ratings else 0.0

    @property
    def rating_count(self):
        return len([r for r in self.ratings if not r.deleted_at])

    @property
    def total_enrolled_students(self):
        return len(self.students)

