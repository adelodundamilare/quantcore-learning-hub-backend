from sqlalchemy import Column, Integer, ForeignKey
from app.core.database import Base

user_school_association = Table(
    "user_school_association",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("school_id", Integer, ForeignKey("schools.id"), primary_key=True),
    Column("role_id", Integer, ForeignKey("roles.id"), nullable=False),
)
