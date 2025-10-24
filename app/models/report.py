from sqlalchemy import Column, ForeignKey, Integer, String, Float, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime

class TradingLeaderboardSnapshot(Base):
    __tablename__ = "trading_leaderboard_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, index=True)
    student_full_name = Column(String, index=True)
    student_email = Column(String, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), index=True)
    starting_capital = Column(Float)
    current_balance = Column(Float)
    trading_profit = Column(Float, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

class LeaderboardSnapshot(Base):
    __tablename__ = "leaderboard_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, index=True)
    student_full_name = Column(String, index=True)
    student_email = Column(String, index=True)
    lessons_completed = Column(Integer)
    accumulated_exam_score = Column(Float)
    total_rewards = Column(Integer)
    school_id = Column(Integer, ForeignKey("schools.id"), index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
