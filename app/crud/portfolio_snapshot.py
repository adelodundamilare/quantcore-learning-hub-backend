from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from app.models.portfolio_snapshot import PortfolioSnapshot
from app.crud.base import CRUDBase


class CRUDPortfolioSnapshot(CRUDBase[PortfolioSnapshot, dict, dict]):
    def get_by_user_and_date(
        self,
        db: Session,
        user_id: int,
        snapshot_date: date
    ) -> PortfolioSnapshot:
        return db.query(PortfolioSnapshot).filter(
            and_(
                PortfolioSnapshot.user_id == user_id,
                PortfolioSnapshot.snapshot_date == snapshot_date
            )
        ).first()

    def get_multi_by_user_in_range(
        self,
        db: Session,
        user_id: int,
        from_date: datetime,
        to_date: datetime,
        skip: int = 0,
        limit: int = 100
    ) -> list:
        return db.query(PortfolioSnapshot).filter(
            and_(
                PortfolioSnapshot.user_id == user_id,
                PortfolioSnapshot.snapshot_date >= from_date,
                PortfolioSnapshot.snapshot_date <= to_date
            )
        ).order_by(PortfolioSnapshot.snapshot_date.asc()).offset(skip).limit(limit).all()

    def get_latest_by_user(
        self,
        db: Session,
        user_id: int
    ) -> PortfolioSnapshot:
        return db.query(PortfolioSnapshot).filter(
            PortfolioSnapshot.user_id == user_id
        ).order_by(desc(PortfolioSnapshot.snapshot_date)).first()

    def get_multi_by_user(
        self,
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> list:
        return db.query(PortfolioSnapshot).filter(
            PortfolioSnapshot.user_id == user_id
        ).order_by(desc(PortfolioSnapshot.snapshot_date)).offset(skip).limit(limit).all()


portfolio_snapshot = CRUDPortfolioSnapshot(PortfolioSnapshot)
