from sqlalchemy import Column, Integer, String, Table, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.role import role_permissions

class Permission(Base):
    __tablename__ = "permissions"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False) # e.g., "users:create", "assignments:view"
    
    roles = relationship(
        "Role", secondary=role_permissions, back_populates="permissions"
    )
