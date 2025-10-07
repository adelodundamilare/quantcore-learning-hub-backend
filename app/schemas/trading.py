from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime
from app.core.constants import OrderTypeEnum, OrderStatusEnum

class StockQuoteSchema(BaseModel):
    symbol: str
    price: float
    change: float
    change_percent: float
    high: float
    low: float
    open: float
    volume: float
    timestamp: datetime

class CompanyDetailsSchema(BaseModel):
    symbol: str
    name: str
    description: Optional[str] = None
    ceo: Optional[str] = None
    employees: Optional[int] = None
    headquarters: Optional[str] = None
    founded: Optional[str] = None
    market_cap: Optional[float] = None

class WatchlistItemBase(BaseModel):
    symbol: str

class WatchlistItemCreate(WatchlistItemBase):
    pass

class WatchlistItem(WatchlistItemBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class WatchlistItemUpdate(WatchlistItemBase):
    symbol: Optional[str] = None

class AccountBalanceSchema(BaseModel):
    id: int
    user_id: int
    balance: float
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class PortfolioPositionSchema(BaseModel):
    id: int
    user_id: int
    symbol: str
    quantity: int
    average_price: float
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class TradeOrderBase(BaseModel):
    symbol: str
    order_type: OrderTypeEnum
    quantity: int
    price: float

class TradeOrderCreate(TradeOrderBase):
    pass

class TradeOrder(TradeOrderBase):
    id: int
    user_id: int
    status: OrderStatusEnum
    executed_price: Optional[float] = None
    executed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class HistoricalDataPointSchema(BaseModel):
    open: float
    high: float
    low: float
    close: float
    volume: float
    timestamp: datetime

class HistoricalDataSchema(BaseModel):
    symbol: str
    results_count: int
    results: List[HistoricalDataPointSchema]
