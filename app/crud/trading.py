from typing import List, Optional
from sqlalchemy.orm import Session
from app.crud.base import CRUDBase
from app.models.trading import WatchlistItem, AccountBalance, PortfolioPosition, TradeOrder
from app.schemas.trading import WatchlistItemCreate, WatchlistItemUpdate, AccountBalanceSchema, PortfolioPositionSchema, TradeOrderCreate, TradeOrder

class CRUDWatchlistItem(CRUDBase[WatchlistItem, WatchlistItemCreate, WatchlistItemUpdate]):
    def get_multi_by_user(self, db: Session, *, user_id: int, skip: int = 0, limit: int = 100) -> List[WatchlistItem]:
        return db.query(self.model).filter(self.model.user_id == user_id).offset(skip).limit(limit).all()

    def get_by_user_and_symbol(self, db: Session, *, user_id: int, symbol: str) -> Optional[WatchlistItem]:
        return db.query(self.model).filter(self.model.user_id == user_id, self.model.symbol == symbol).first()

watchlist_item = CRUDWatchlistItem(WatchlistItem)

class CRUDAccountBalance(CRUDBase[AccountBalance, AccountBalanceSchema, AccountBalanceSchema]):
    def get_by_user_id(self, db: Session, user_id: int) -> Optional[AccountBalance]:
        return db.query(self.model).filter(self.model.user_id == user_id).first()

account_balance = CRUDAccountBalance(AccountBalance)

class CRUDPortfolioPosition(CRUDBase[PortfolioPosition, PortfolioPositionSchema, PortfolioPositionSchema]):
    def get_by_user_and_symbol(self, db: Session, user_id: int, symbol: str) -> Optional[PortfolioPosition]:
        return db.query(self.model).filter(self.model.user_id == user_id, self.model.symbol == symbol).first()

    def get_multi_by_user(self, db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[PortfolioPosition]:
        return db.query(self.model).filter(self.model.user_id == user_id).offset(skip).limit(limit).all()

portfolio_position = CRUDPortfolioPosition(PortfolioPosition)

class CRUDTradeOrder(CRUDBase[TradeOrder, TradeOrderCreate, TradeOrder]):
    def get_multi_by_user(self, db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[TradeOrder]:
        return db.query(self.model).filter(self.model.user_id == user_id).offset(skip).limit(limit).all()

trade_order = CRUDTradeOrder(TradeOrder)
