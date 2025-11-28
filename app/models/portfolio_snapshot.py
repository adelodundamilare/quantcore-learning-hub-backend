from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class PortfolioSnapshot(Base):
    __tablename__ = "portfolio_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    snapshot_date = Column(DateTime(timezone=True), nullable=False, index=True)
    total_portfolio_value = Column(Float, nullable=False)
    cash_balance = Column(Float, nullable=False)
    stocks_value = Column(Float, nullable=False)
    holdings = Column(JSON, nullable=False)
    realized_pnl = Column(Float, default=0.0, nullable=False)
    unrealized_pnl = Column(Float, default=0.0, nullable=False)
    total_pnl = Column(Float, default=0.0, nullable=False)
    percent_change = Column(Float, default=0.0, nullable=False)
    percent_change_from_start = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="portfolio_snapshots")
