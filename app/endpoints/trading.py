from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import Optional, List, Dict
import asyncio
import logging

from app.core.constants import OrderTypeEnum
from app.schemas.response import APIResponse
from app.utils import deps
from app.schemas.user import UserContext
from app.schemas.trading import HistoricalDataPointSchema, HistoricalDataSchema, StockQuoteSchema, WatchlistItem, WatchlistItemCreate, AccountBalanceSchema, PortfolioPositionSchema, TradeOrderCreate, TradeOrder, CompanyDetailsSchema
from app.services.polygon import polygon_service
from app.services.trading import trading_service

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.price_cache: Dict[str, dict] = {}

    async def connect(self, websocket: WebSocket, symbol: str):
        await websocket.accept()
        if symbol not in self.active_connections:
            self.active_connections[symbol] = []
        self.active_connections[symbol].append(websocket)
        logger.info(f"Client connected to {symbol}. Total connections: {len(self.active_connections[symbol])}")

    def disconnect(self, websocket: WebSocket, symbol: str):
        if symbol in self.active_connections:
            self.active_connections[symbol].remove(websocket)
            if not self.active_connections[symbol]:
                del self.active_connections[symbol]
            logger.info(f"Client disconnected from {symbol}")

    async def broadcast(self, symbol: str, data: dict):
        if symbol in self.active_connections:
            disconnected = []
            for connection in self.active_connections[symbol]:
                try:
                    await connection.send_json(data)
                except Exception as e:
                    logger.error(f"Error broadcasting to client: {e}")
                    disconnected.append(connection)

            for conn in disconnected:
                self.disconnect(conn, symbol)

manager = ConnectionManager()

async def stream_prices():
    while True:
        try:
            symbols = list(manager.active_connections.keys())

            for symbol in symbols:
                try:
                    quote = await polygon_service.get_latest_quote(symbol, use_cache=False)
                    if quote:
                        await manager.broadcast(symbol, {
                            "type": "price_update",
                            "data": quote
                        })
                except Exception as e:
                    logger.error(f"Error streaming price for {symbol}: {e}")

            await asyncio.sleep(5)

        except Exception as e:
            logger.error(f"Error in stream_prices: {e}")
            await asyncio.sleep(10)

router = APIRouter()

@router.on_event("startup")
async def startup_event():
    asyncio.create_task(stream_prices())
    logger.info("Price streaming task started")

@router.get("/stocks/{ticker}/quote", response_model=APIResponse[StockQuoteSchema])
async def get_stock_quote(
    ticker: str,
    db: Session = Depends(deps.get_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    quote_data = await polygon_service.get_latest_quote(ticker)
    if not quote_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Quote for {ticker} not found.")

    try:
        stock_quote = StockQuoteSchema(
            symbol=quote_data.get('T', ticker),
            price=quote_data.get('p'),
            timestamp=quote_data.get('t')
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error parsing quote data: {e}")

    return APIResponse(message=f"Latest quote for {ticker} retrieved successfully", data=stock_quote)

@router.get("/stocks/{ticker}/details", response_model=APIResponse[CompanyDetailsSchema])
async def get_company_details(
    ticker: str,
    db: Session = Depends(deps.get_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    details_data = await polygon_service.get_company_details(ticker)
    if not details_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Details for {ticker} not found.")

    try:
        company_details = CompanyDetailsSchema(**details_data)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error parsing company details: {e}")

    return APIResponse(message=f"Company details for {ticker} retrieved successfully", data=company_details)

@router.post("/watchlist", response_model=APIResponse[WatchlistItem], status_code=status.HTTP_201_CREATED)
def add_stock_to_watchlist(
    watchlist_item_in: WatchlistItemCreate,
    db: Session = Depends(deps.get_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    new_item = trading_service.add_stock_to_watchlist(db, user_id=context.user.id, watchlist_item_in=watchlist_item_in)
    return APIResponse(message="Stock added to watchlist successfully", data=new_item)

@router.delete("/watchlist/{symbol}", response_model=APIResponse[WatchlistItem])
def remove_stock_from_watchlist(
    symbol: str,
    db: Session = Depends(deps.get_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    deleted_item = trading_service.remove_stock_from_watchlist(db, user_id=context.user.id, symbol=symbol)
    return APIResponse(message="Stock removed from watchlist successfully", data=deleted_item)

@router.get("/watchlist", response_model=APIResponse[List[WatchlistItem]])
def get_user_watchlist(
    db: Session = Depends(deps.get_db),
    context: UserContext = Depends(deps.get_current_user_with_context),
    skip: int = 0,
    limit: int = 100
):
    watchlist = trading_service.get_user_watchlist(db, user_id=context.user.id, skip=skip, limit=limit)
    return APIResponse(message="User watchlist retrieved successfully", data=watchlist)

@router.get("/account/balance", response_model=APIResponse[AccountBalanceSchema])
def get_account_balance(
    db: Session = Depends(deps.get_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    balance = trading_service.get_account_balance(db, user_id=context.user.id)
    return APIResponse(message="Account balance retrieved successfully", data=balance)

@router.get("/portfolio", response_model=APIResponse[List[PortfolioPositionSchema]])
def get_portfolio(
    db: Session = Depends(deps.get_db),
    context: UserContext = Depends(deps.get_current_user_with_context),
    skip: int = 0,
    limit: int = 100
):
    portfolio = trading_service.get_portfolio(db, user_id=context.user.id, skip=skip, limit=limit)
    return APIResponse(message="User portfolio retrieved successfully", data=portfolio)

@router.post("/trade/buy", response_model=APIResponse[TradeOrder], status_code=status.HTTP_201_CREATED)
async def buy_stock(
    order_in: TradeOrderCreate,
    db: Session = Depends(deps.get_transactional_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    if order_in.order_type != OrderTypeEnum.BUY:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order type must be BUY.")
    new_order = await trading_service.place_order(db, user_id=context.user.id, order_in=order_in)
    return APIResponse(message="Buy order placed successfully", data=new_order)

@router.post("/trade/sell", response_model=APIResponse[TradeOrder], status_code=status.HTTP_201_CREATED)
async def sell_stock(
    order_in: TradeOrderCreate,
    db: Session = Depends(deps.get_transactional_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    if order_in.order_type != OrderTypeEnum.SELL:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Order type must be SELL.")
    new_order = await trading_service.place_order(db, user_id=context.user.id, order_in=order_in)
    return APIResponse(message="Sell order placed successfully", data=new_order)

@router.get("/trade/history", response_model=APIResponse[List[TradeOrder]])
def get_trade_history(
    db: Session = Depends(deps.get_db),
    context: UserContext = Depends(deps.get_current_user_with_context),
    skip: int = 0,
    limit: int = 100
):
    history = trading_service.get_trade_history(db, user_id=context.user.id, skip=skip, limit=limit)
    return APIResponse(message="Trade history retrieved successfully", data=history)

@router.websocket("/ws/stocks/{ticker}")
async def websocket_stock_quote(
    websocket: WebSocket,
    ticker: str,
    context: UserContext = Depends(deps.get_current_user_with_context) # Authenticate WebSocket
):
    await manager.connect(websocket, ticker)
    try:
        # Send initial price
        initial_quote = await polygon_service.get_latest_quote(ticker)
        if initial_quote:
            await websocket.send_json({
                "type": "price_update",
                "data": StockQuoteSchema(**initial_quote).model_dump()
            })

        while True:
            # Keep connection alive, client can send messages if needed
            await websocket.receive_text() # Expecting client to send something to keep alive or for commands
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for {ticker}")
    except Exception as e:
        logger.error(f"WebSocket error for {ticker}: {e}")
    finally:
        manager.disconnect(websocket, ticker)

@router.get("/stocks/{ticker}/history", response_model=APIResponse[HistoricalDataSchema])
async def get_historical_data(
    ticker: str,
    from_date: datetime = Depends(lambda d: datetime.strptime(d, "%Y-%m-%d")),
    to_date: datetime = Depends(lambda d: datetime.strptime(d, "%Y-%m-%d")),
    multiplier: int = 1,
    timespan: str = "day",
    db: Session = Depends(deps.get_db),
    context: UserContext = Depends(deps.get_current_user_with_context)
):
    historical_data = await polygon_service.get_historical_data(ticker, from_date, to_date, multiplier, timespan)
    if not historical_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Historical data for {ticker} not found.")

    try:
        historical_schema = HistoricalDataSchema(
            symbol=historical_data.get('symbol', ticker),
            results_count=historical_data.get('results_count', 0),
            results=[HistoricalDataPointSchema(**res) for res in historical_data.get('results', [])]
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error parsing historical data: {e}")

    return APIResponse(message=f"Historical data for {ticker} retrieved successfully", data=historical_schema)

