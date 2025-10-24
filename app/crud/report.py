from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from app.crud.base import CRUDBase
from app.models.report import TradingLeaderboardSnapshot, LeaderboardSnapshot
from app.schemas.report import TradingLeaderboardEntrySchema, LeaderboardEntrySchema

class CRUDTradingLeaderboardSnapshot(CRUDBase[TradingLeaderboardSnapshot, TradingLeaderboardEntrySchema, TradingLeaderboardEntrySchema]):
    def get_latest_snapshot(self, db: Session) -> Optional[TradingLeaderboardSnapshot]:
        return db.query(self.model).order_by(self.model.timestamp.desc()).first()

    def get_all_snapshots(self, db: Session, skip: int = 0, limit: int = 100) -> List[TradingLeaderboardSnapshot]:
        return db.query(self.model).order_by(self.model.timestamp.desc()).offset(skip).limit(limit).all()

    def get_all_snapshots_for_school(self, db: Session, school_id: int, skip: int = 0, limit: int = 100) -> List[TradingLeaderboardSnapshot]:
        return db.query(self.model).filter(self.model.school_id == school_id).order_by(self.model.trading_profit.desc(), self.model.timestamp.desc()).offset(skip).limit(limit).all()

    def delete_old_snapshots(self, db: Session, older_than_minutes: int = 60):
        threshold = datetime.utcnow() - timedelta(minutes=older_than_minutes)
        db.query(self.model).filter(self.model.timestamp < threshold).delete()
        db.commit()

    def delete_old_snapshots_for_school(self, db: Session, school_id: int, older_than_minutes: int = 60):
        threshold = datetime.utcnow() - timedelta(minutes=older_than_minutes)
        db.query(self.model).filter(self.model.school_id == school_id, self.model.timestamp < threshold).delete()
        db.commit()

    def count_snapshots_for_school(self, db: Session, school_id: int) -> int:
        return db.query(self.model).filter(self.model.school_id == school_id).count()

    def bulk_create_trading_leaderboard_snapshots(self, db: Session, snapshots_data: List[dict]):
        db.bulk_insert_mappings(self.model, snapshots_data)
        db.commit()

trading_leaderboard_snapshot = CRUDTradingLeaderboardSnapshot(TradingLeaderboardSnapshot)

class CRUDLeaderboardSnapshot(CRUDBase[LeaderboardSnapshot, LeaderboardEntrySchema, LeaderboardEntrySchema]):
    def get_latest_snapshot(self, db: Session) -> Optional[LeaderboardSnapshot]:
        return db.query(self.model).order_by(self.model.timestamp.desc()).first()

    def get_all_snapshots(self, db: Session, skip: int = 0, limit: int = 100) -> List[LeaderboardSnapshot]:
        return db.query(self.model).order_by(self.model.timestamp.desc()).offset(skip).limit(limit).all()

    def get_all_snapshots_for_school(self, db: Session, school_id: int, skip: int = 0, limit: int = 100) -> List[LeaderboardSnapshot]:
        return db.query(self.model).filter(self.model.school_id == school_id).order_by(self.model.total_rewards.desc(), self.model.timestamp.desc()).offset(skip).limit(limit).all()

    def delete_old_snapshots(self, db: Session, older_than_minutes: int = 60):
        threshold = datetime.utcnow() - timedelta(minutes=older_than_minutes)
        db.query(self.model).filter(self.model.timestamp < threshold).delete()
        db.commit()

    def delete_old_snapshots_for_school(self, db: Session, school_id: int, older_than_minutes: int = 60):
        threshold = datetime.utcnow() - timedelta(minutes=older_than_minutes)
        db.query(self.model).filter(self.model.school_id == school_id, self.model.timestamp < threshold).delete()
        db.commit()

    def count_snapshots_for_school(self, db: Session, school_id: int) -> int:
        return db.query(self.model).filter(self.model.school_id == school_id).count()

    def bulk_create_leaderboard_snapshots(self, db: Session, snapshots_data: List[dict]):
        db.bulk_insert_mappings(self.model, snapshots_data)
        db.commit()

leaderboard_snapshot = CRUDLeaderboardSnapshot(LeaderboardSnapshot)
