from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
from app.core.constants import OrderTypeEnum, OrderStatusEnum

class UserWatchlist(Base):
    __tablename__ = "user_watchlists"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="user_watchlists")
    stocks = relationship("WatchlistStock", back_populates="watchlist", cascade="all, delete-orphan")

class WatchlistStock(Base):
    __tablename__ = "watchlist_stocks"

    id = Column(Integer, primary_key=True, index=True)
    watchlist_id = Column(Integer, ForeignKey("user_watchlists.id"), nullable=False)
    symbol = Column(String, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    watchlist = relationship("UserWatchlist", back_populates="stocks")

class AccountBalance(Base):
    __tablename__ = "account_balances"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    balance = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="account_balance")

class PortfolioPosition(Base):
    __tablename__ = "portfolio_positions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol = Column(String, index=True, nullable=False)
    quantity = Column(Integer, nullable=False)
    average_price = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="portfolio_positions")

class TradeOrder(Base):
    __tablename__ = "trade_orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol = Column(String, index=True, nullable=False)
    order_type = Column(Enum(OrderTypeEnum), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    status = Column(Enum(OrderStatusEnum), nullable=False, default=OrderStatusEnum.PENDING)
    executed_price = Column(Float, nullable=True)
    total_amount = Column(Float, nullable=False)
    executed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="trade_orders")
