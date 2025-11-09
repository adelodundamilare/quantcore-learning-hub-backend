from sqlalchemy import Boolean, Column, String, Integer, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.models.user_school_association import UserSchoolAssociation
from app.models.course import course_teachers_association, course_students_association

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=True)
    avatar = Column(String, nullable=True)
    is_active = Column(Boolean(), default=True)
    auth_provider = Column(String, default="email")  # email, google, apple

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Many-to-many relationship with School via the association model
    school_associations = relationship("UserSchoolAssociation", back_populates="user")
    schools = relationship(
        "School",
        secondary="user_school_association",
        back_populates="users",
        primaryjoin="User.id == UserSchoolAssociation.user_id",
        secondaryjoin="School.id == UserSchoolAssociation.school_id",
        viewonly=True
    )
    teaching_courses = relationship("Course", secondary=course_teachers_association, back_populates="teachers")
    enrolled_courses = relationship("Course", secondary=course_students_association, back_populates="students")
    exam_attempts = relationship("ExamAttempt", back_populates="user", cascade="all, delete-orphan")
    user_answers = relationship("UserAnswer", back_populates="user", cascade="all, delete-orphan")
    course_enrollments = relationship("CourseEnrollment", back_populates="user")
    course_ratings = relationship("CourseRating", back_populates="user")
    user_watchlists = relationship("UserWatchlist", back_populates="user", cascade="all, delete-orphan")
    account_balance = relationship("AccountBalance", back_populates="user", uselist=False, cascade="all, delete-orphan")
    portfolio_positions = relationship("PortfolioPosition", back_populates="user", cascade="all, delete-orphan")
    trade_orders = relationship("TradeOrder", back_populates="user", cascade="all, delete-orphan")
    stripe_customer = relationship("StripeCustomer", back_populates="user", uselist=False, cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")
