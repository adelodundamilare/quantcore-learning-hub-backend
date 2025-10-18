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

class StockSchema(BaseModel):
    symbol: str
    name: str
    market: Optional[str] = None
    locale: Optional[str] = None
    primary_exchange: Optional[str] = None
    type: Optional[str] = None
    active: Optional[bool] = None
    currency_name: Optional[str] = None
    cik: Optional[str] = None
    composite_figi: Optional[str] = None
    share_class_figi: Optional[str] = None
    last_updated_utc: Optional[str] = None
    delisted_utc: Optional[str] = None
    sparkline_data: Optional[List[float]] = None

class CompanyDetailsSchema(BaseModel):
    symbol: str
    name: str
    description: Optional[str] = None
    ceo: Optional[str] = None
    employees: Optional[int] = None
    headquarters: Optional[str] = None
    founded: Optional[str] = None
    market_cap: Optional[float] = None

class StockDetailsSchema(BaseModel):
    symbol: str
    name: str
    price: Optional[float] = None
    change: Optional[float] = None
    change_percent: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    open: Optional[float] = None
    volume: Optional[float] = None
    avg_volume: Optional[float] = None
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    description: Optional[str] = None
    ceo: Optional[str] = None
    employees: Optional[int] = None
    headquarters: Optional[str] = None
    founded: Optional[str] = None
    sparkline_data: Optional[List[float]] = None

class WatchlistItemBase(BaseModel):
    symbol: str

class WatchlistItemCreate(WatchlistItemBase):
    pass

class WatchlistItem(WatchlistItemBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    sparkline_data: Optional[List[float]] = None

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

class AccountBalanceCreate(BaseModel):
    pass

class AccountBalanceUpdate(BaseModel):
    pass

class PortfolioPositionSchema(BaseModel):
    id: int
    user_id: int
    symbol: str
    quantity: int
    average_price: float
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class PortfolioPositionCreate(BaseModel):
    pass

class PortfolioPositionUpdate(BaseModel):
    pass

class TradeOrderBase(BaseModel):
    symbol: str
    order_type: OrderTypeEnum
    quantity: int
    price: float

class TradeOrderCreate(TradeOrderBase):
    pass

class TradeOrderUpdate(TradeOrderBase):
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
