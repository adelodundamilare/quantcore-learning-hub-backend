from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.user_school_association import user_school_association

class School(Base):
    __tablename__ = "schools"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    # Add other school-specific fields here

    users = relationship(
        "User",
        secondary=user_school_association,
        back_populates="schools"
    )
    courses = relationship("Course", back_populates="school")
    invoices = relationship("Invoice", back_populates="school")
