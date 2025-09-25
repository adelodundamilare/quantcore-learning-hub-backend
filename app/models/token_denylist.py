from sqlalchemy import Column, Integer, String, DateTime

from app.core.database import Base

class TokenDenylist(Base):
    __tablename__ = "token_denylist"

    id = Column(Integer, primary_key=True, index=True)
    jti = Column(String, nullable=False, index=True)
    exp = Column(DateTime(timezone=True), nullable=False)
