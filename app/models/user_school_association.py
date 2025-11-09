from sqlalchemy import Column, Integer, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.core.constants import CourseLevelEnum

class UserSchoolAssociation(Base):
    __tablename__ = "user_school_association"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    school_id = Column(Integer, ForeignKey("schools.id"), primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    level = Column(Enum(CourseLevelEnum), nullable=True)

    # Soft delete
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Audit fields
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="school_associations")
    school = relationship("School", back_populates="user_associations")
    role = relationship("Role")

# Keep the table reference for backward compatibility
user_school_association = UserSchoolAssociation.__table__
