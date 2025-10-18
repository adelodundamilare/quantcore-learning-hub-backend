from typing import List, Optional
from sqlalchemy.orm import Session
from app.crud.base import CRUDBase
from app.models.trading import UserWatchlist, WatchlistStock, AccountBalance, PortfolioPosition, TradeOrder
from app.schemas.trading import (
    UserWatchlistCreate,
    UserWatchlistUpdate,
    WatchlistStockCreate,
    WatchlistStockUpdate,
    AccountBalanceCreate,
    AccountBalanceUpdate,
    PortfolioPositionCreate,
    PortfolioPositionUpdate,
    TradeOrderCreate,
    TradeOrderUpdate
)

class CRUDUserWatchlist(CRUDBase[UserWatchlist, UserWatchlistCreate, UserWatchlistUpdate]):
    def get_multi_by_user(self, db: Session, *, user_id: int, skip: int = 0, limit: int = 100) -> List[UserWatchlist]:
        return db.query(self.model).filter(self.model.user_id == user_id).offset(skip).limit(limit).all()

    def get_by_user_and_name(self, db: Session, *, user_id: int, name: str) -> Optional[UserWatchlist]:
        return db.query(self.model).filter(
            self.model.user_id == user_id
        ).filter(
            self.model.name == name
        ).first()

user_watchlist = CRUDUserWatchlist(UserWatchlist)

class CRUDWatchlistStock(CRUDBase[WatchlistStock, WatchlistStockCreate, WatchlistStockUpdate]):
    def get_by_watchlist_and_symbol(self, db: Session, *, watchlist_id: int, symbol: str) -> Optional[WatchlistStock]:
        return db.query(self.model).filter(
            self.model.watchlist_id == watchlist_id
        ).filter(
            self.model.symbol == symbol
        ).first()

watchlist_stock = CRUDWatchlistStock(WatchlistStock)

class CRUDAccountBalance(CRUDBase[AccountBalance, AccountBalanceCreate, AccountBalanceUpdate]):
    def get_by_user_id(self, db: Session, user_id: int) -> Optional[AccountBalance]:
        return db.query(self.model).filter(self.model.user_id == user_id).first()

account_balance = CRUDAccountBalance(AccountBalance)

class CRUDPortfolioPosition(CRUDBase[PortfolioPosition, PortfolioPositionCreate, PortfolioPositionUpdate]):
    def get_by_user_and_symbol(self, db: Session, user_id: int, symbol: str) -> Optional[PortfolioPosition]:
        return db.query(self.model).filter(
            self.model.user_id == user_id
        ).filter(
            self.model.symbol == symbol
        ).first()

    def get_multi_by_user(self, db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[PortfolioPosition]:
        return db.query(self.model).filter(self.model.user_id == user_id).offset(skip).limit(limit).all()

portfolio_position = CRUDPortfolioPosition(PortfolioPosition)

class CRUDTradeOrder(CRUDBase[TradeOrder, TradeOrderCreate, TradeOrderUpdate]):
    def get_multi_by_user(self, db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[TradeOrder]:
        return db.query(self.model).filter(self.model.user_id == user_id).offset(skip).limit(limit).all()

trade_order = CRUDTradeOrder(TradeOrder)