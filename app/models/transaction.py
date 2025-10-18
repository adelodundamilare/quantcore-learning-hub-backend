from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    initiator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    amount = Column(Float, nullable=False)
    transaction_type = Column(String, nullable=False) # e.g., "deposit", "withdrawal", "fund_addition"
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", foreign_keys=[user_id])
    initiator = relationship("User", foreign_keys=[initiator_id])
