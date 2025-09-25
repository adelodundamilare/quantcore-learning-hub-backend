from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum

class TokenType(str, enum.Enum):
    PASSWORD_RESET = "password_reset"
    ACCOUNT_VERIFICATION = "account_verification"

class OneTimeToken(Base):
    __tablename__ = "one_time_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String, unique=True, index=True, nullable=False)
    token_type = Column(Enum(TokenType), nullable=False)
    expires_at = Column(DateTime, nullable=False)

    user = relationship("User")
