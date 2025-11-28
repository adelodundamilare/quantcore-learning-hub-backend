from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime


class PortfolioSnapshotSchema(BaseModel):
    id: int
    user_id: int
    snapshot_date: datetime
    total_portfolio_value: float
    cash_balance: float
    stocks_value: float
    holdings: Dict[str, Any]
    realized_pnl: float
    unrealized_pnl: float
    total_pnl: float
    percent_change: float
    percent_change_from_start: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PortfolioSnapshotCreate(BaseModel):
    user_id: int
    snapshot_date: datetime
    total_portfolio_value: float
    cash_balance: float
    stocks_value: float
    holdings: Dict[str, Any]
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    total_pnl: float = 0.0
    percent_change: float = 0.0
    percent_change_from_start: float = 0.0


class PortfolioSnapshotUpdate(BaseModel):
    total_portfolio_value: Optional[float] = None
    cash_balance: Optional[float] = None
    stocks_value: Optional[float] = None
    holdings: Optional[Dict[str, Any]] = None
    realized_pnl: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    total_pnl: Optional[float] = None
    percent_change: Optional[float] = None
    percent_change_from_start: Optional[float] = None
