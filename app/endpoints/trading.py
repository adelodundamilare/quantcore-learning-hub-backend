from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict
from collections import defaultdict
import asyncio
import logging
import socketio # type: ignore

from app.core.constants import OrderTypeEnum
from app.schemas.response import APIResponse
from app.utils import deps
from app.schemas.user import UserContext
from app.schemas.trading import (
    HistoricalDataPointSchema,
    HistoricalDataSchema,
    StockQuoteSchema,
    WatchlistItem,
    WatchlistItemCreate,
    AccountBalanceSchema,
    PortfolioPositionSchema,
    TradeOrderCreate,
    TradeOrder,
    CompanyDetailsSchema
)
from app.services.polygon import polygon_service
from app.services.trading import trading_service
# from app.core.security import verify_token

logger = logging.getLogger(__name__)

user_sessions: Dict[str, dict] = {}
subscribe_limits: Dict[int, list] = defaultdict(list)

async def stream_prices_socketio(sio_server: socketio.AsyncServer):
    while True:
        try:
            subscribed_symbols = set()

            for room_name in sio_server.manager.rooms['/'].keys():
                if (room_name not in sio_server.eio.sid_namespaces and
                    not room_name.startswith('_') and
                    len(room_name) <= 10 and
                    room_name.isupper()):
                    subscribed_symbols.add(room_name)

            if not subscribed_symbols:
                await asyncio.sleep(5)
                continue

            for symbol in subscribed_symbols:
                try:
                    quote = await polygon_service.get_latest_quote(symbol, use_cache=False)
                    if quote:
                        await sio_server.emit('price_update', {
                            'symbol': symbol,
                            'data': quote
                        }, room=symbol)
                except Exception as e:
                    logger.error(f"Error streaming price for {symbol}: {e}")
                    continue

            await asyncio.sleep(5)

        except Exception as e:
            logger.error(f"Error in stream_prices_socketio: {e}")
            await asyncio.sleep(10)

def create_trading_router(sio_server: socketio.AsyncServer):
    router = APIRouter()

    @router.on_event("startup")
    async def startup():
        asyncio.create_task(stream_prices_socketio(sio_server))
        logger.info("Socket.IO price streaming started")

    @sio_server.event
    async def connect(sid, environ, auth):
        try:
            if not auth or 'token' not in auth:
                logger.warning(f"Connection rejected for {sid}: No token")
                return False

            token = auth['token']
            user = 'verify_token(token)'

            if not user:
                logger.warning(f"Connection rejected for {sid}: Invalid token")
                return False

            user_sessions[sid] = {
                'user_id': user.id,
                'connected_at': datetime.utcnow(),
                'subscriptions': set()
            }

            await sio_server.save_session(sid, {'user_id': user.id})
            logger.info(f"Client {sid} connected (User: {user.id})")

            await sio_server.emit('connected', {
                'status': 'success',
                'message': 'Connected successfully'
            }, room=sid)

            return True

        except Exception as e:
            logger.error(f"Connection error for {sid}: {e}")
            return False

    @sio_server.event
    async def disconnect(sid):
        user_id = user_sessions.get(sid, {}).get('user_id')

        for room in list(sio_server.rooms(sid)):
            if room != sid:
                sio_server.leave_room(sid, room)

        if sid in user_sessions:
            del user_sessions[sid]

        logger.info(f"Client {sid} disconnected (User: {user_id})")

    @sio_server.on('subscribe')
    async def handle_subscribe(sid, data):
        try:
            symbol = data.get('symbol')

            if not symbol:
                await sio_server.emit('error', {
                    'message': 'Symbol is required'
                }, room=sid)
                return

            symbol = symbol.upper().strip()

            session = await sio_server.get_session(sid)
            if not session or 'user_id' not in session:
                await sio_server.emit('error', {
                    'message': 'Not authenticated'
                }, room=sid)
                return

            user_id = session['user_id']
            now = datetime.utcnow()

            subscribe_limits[user_id] = [
                t for t in subscribe_limits[user_id]
                if now - t < timedelta(minutes=1)
            ]

            if len(subscribe_limits[user_id]) >= 20:
                await sio_server.emit('error', {
                    'message': 'Rate limit exceeded. Max 20 subscriptions per minute'
                }, room=sid)
                return

            subscribe_limits[user_id].append(now)

            sio_server.enter_room(sid, symbol)

            if sid in user_sessions:
                user_sessions[sid]['subscriptions'].add(symbol)

            logger.info(f"Client {sid} subscribed to {symbol}")

            initial_quote = await polygon_service.get_latest_quote(symbol)
            if initial_quote:
                await sio_server.emit('price_update', {
                    'symbol': symbol,
                    'data': initial_quote
                }, room=sid)

            await sio_server.emit('subscribed', {
                'symbol': symbol,
                'status': 'success'
            }, room=sid)

        except Exception as e:
            logger.error(f"Subscribe error for {sid}: {e}")
            await sio_server.emit('error', {
                'message': f'Failed to subscribe: {str(e)}'
            }, room=sid)

    @sio_server.on('unsubscribe')
    async def handle_unsubscribe(sid, data):
        try:
            symbol = data.get('symbol')

            if not symbol:
                await sio_server.emit('error', {
                    'message': 'Symbol is required'
                }, room=sid)
                return

            symbol = symbol.upper().strip()

            sio_server.leave_room(sid, symbol)

            if sid in user_sessions:
                user_sessions[sid]['subscriptions'].discard(symbol)

            logger.info(f"Client {sid} unsubscribed from {symbol}")

            await sio_server.emit('unsubscribed', {
                'symbol': symbol,
                'status': 'success'
            }, room=sid)

        except Exception as e:
            logger.error(f"Unsubscribe error for {sid}: {e}")
            await sio_server.emit('error', {
                'message': f'Failed to unsubscribe: {str(e)}'
            }, room=sid)

    @sio_server.on('ping')
    async def handle_ping(sid, data):
        await sio_server.emit('pong', {
            'timestamp': datetime.utcnow().isoformat()
        }, room=sid)

    @router.get("/stocks/{ticker}/quote", response_model=APIResponse[StockQuoteSchema])
    async def get_stock_quote(
        ticker: str,
        db: Session = Depends(deps.get_db),
        context: UserContext = Depends(deps.get_current_user_with_context)
    ):
        quote_data = await polygon_service.get_latest_quote(ticker)
        if not quote_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Quote for {ticker} not found."
            )

        try:
            stock_quote = StockQuoteSchema(
                symbol=quote_data.get('T', ticker),
                price=quote_data.get('p'),
                timestamp=quote_data.get('t')
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error parsing quote data: {e}"
            )

        return APIResponse(
            message=f"Latest quote for {ticker} retrieved successfully",
            data=stock_quote
        )

    @router.get("/stocks/{ticker}/details", response_model=APIResponse[CompanyDetailsSchema])
    async def get_company_details(
        ticker: str,
        db: Session = Depends(deps.get_db),
        context: UserContext = Depends(deps.get_current_user_with_context)
    ):
        details_data = await polygon_service.get_company_details(ticker)
        if not details_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Details for {ticker} not found."
            )

        try:
            company_details = CompanyDetailsSchema(**details_data)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error parsing company details: {e}"
            )

        return APIResponse(
            message=f"Company details for {ticker} retrieved successfully",
            data=company_details
        )

    @router.post("/watchlist", response_model=APIResponse[WatchlistItem], status_code=status.HTTP_201_CREATED)
    def add_stock_to_watchlist(
        watchlist_item_in: WatchlistItemCreate,
        db: Session = Depends(deps.get_db),
        context: UserContext = Depends(deps.get_current_user_with_context)
    ):
        new_item = trading_service.add_stock_to_watchlist(
            db,
            user_id=context.user.id,
            watchlist_item_in=watchlist_item_in
        )
        return APIResponse(
            message="Stock added to watchlist successfully",
            data=new_item
        )

    @router.delete("/watchlist/{symbol}", response_model=APIResponse[WatchlistItem])
    def remove_stock_from_watchlist(
        symbol: str,
        db: Session = Depends(deps.get_db),
        context: UserContext = Depends(deps.get_current_user_with_context)
    ):
        deleted_item = trading_service.remove_stock_from_watchlist(
            db,
            user_id=context.user.id,
            symbol=symbol
        )
        return APIResponse(
            message="Stock removed from watchlist successfully",
            data=deleted_item
        )

    @router.get("/watchlist", response_model=APIResponse[List[WatchlistItem]])
    def get_user_watchlist(
        db: Session = Depends(deps.get_db),
        context: UserContext = Depends(deps.get_current_user_with_context),
        skip: int = 0,
        limit: int = 100
    ):
        watchlist = trading_service.get_user_watchlist(
            db,
            user_id=context.user.id,
            skip=skip,
            limit=limit
        )
        return APIResponse(
            message="User watchlist retrieved successfully",
            data=watchlist
        )

    @router.get("/account/balance", response_model=APIResponse[AccountBalanceSchema])
    def get_account_balance(
        db: Session = Depends(deps.get_db),
        context: UserContext = Depends(deps.get_current_user_with_context)
    ):
        balance = trading_service.get_account_balance(db, user_id=context.user.id)
        return APIResponse(
            message="Account balance retrieved successfully",
            data=balance
        )

    @router.get("/portfolio", response_model=APIResponse[List[PortfolioPositionSchema]])
    def get_portfolio(
        db: Session = Depends(deps.get_db),
        context: UserContext = Depends(deps.get_current_user_with_context),
        skip: int = 0,
        limit: int = 100
    ):
        portfolio = trading_service.get_portfolio(
            db,
            user_id=context.user.id,
            skip=skip,
            limit=limit
        )
        return APIResponse(
            message="User portfolio retrieved successfully",
            data=portfolio
        )

    @router.post("/trade/buy", response_model=APIResponse[TradeOrder], status_code=status.HTTP_201_CREATED)
    async def buy_stock(
        order_in: TradeOrderCreate,
        db: Session = Depends(deps.get_transactional_db),
        context: UserContext = Depends(deps.get_current_user_with_context)
    ):
        if order_in.order_type != OrderTypeEnum.BUY:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Order type must be BUY."
            )
        new_order = await trading_service.place_order(
            db,
            user_id=context.user.id,
            order_in=order_in
        )
        return APIResponse(
            message="Buy order placed successfully",
            data=new_order
        )

    @router.post("/trade/sell", response_model=APIResponse[TradeOrder], status_code=status.HTTP_201_CREATED)
    async def sell_stock(
        order_in: TradeOrderCreate,
        db: Session = Depends(deps.get_transactional_db),
        context: UserContext = Depends(deps.get_current_user_with_context)
    ):
        if order_in.order_type != OrderTypeEnum.SELL:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Order type must be SELL."
            )
        new_order = await trading_service.place_order(
            db,
            user_id=context.user.id,
            order_in=order_in
        )
        return APIResponse(
            message="Sell order placed successfully",
            data=new_order
        )

    @router.get("/trade/history", response_model=APIResponse[List[TradeOrder]])
    def get_trade_history(
        db: Session = Depends(deps.get_db),
        context: UserContext = Depends(deps.get_current_user_with_context),
        skip: int = 0,
        limit: int = 100
    ):
        history = trading_service.get_trade_history(
            db,
            user_id=context.user.id,
            skip=skip,
            limit=limit
        )
        return APIResponse(
            message="Trade history retrieved successfully",
            data=history
        )

    @router.get("/stocks/{ticker}/history", response_model=APIResponse[HistoricalDataSchema])
    async def get_historical_data(
        ticker: str,
        from_date: str,
        to_date: str,
        multiplier: int = 1,
        timespan: str = "day",
        db: Session = Depends(deps.get_db),
        context: UserContext = Depends(deps.get_current_user_with_context)
    ):
        try:
            from_dt = datetime.strptime(from_date, "%Y-%m-%d")
            to_dt = datetime.strptime(to_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD"
            )

        if from_dt > to_dt:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="from_date must be before to_date"
            )

        historical_data = await polygon_service.get_historical_data(
            ticker,
            from_dt,
            to_dt,
            multiplier,
            timespan
        )

        if not historical_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Historical data for {ticker} not found."
            )

        try:
            historical_schema = HistoricalDataSchema(
                symbol=historical_data.get('symbol', ticker),
                results_count=historical_data.get('results_count', 0),
                results=[
                    HistoricalDataPointSchema(**res)
                    for res in historical_data.get('results', [])
                ]
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error parsing historical data: {e}"
            )

        return APIResponse(
            message=f"Historical data for {ticker} retrieved successfully",
            data=historical_schema
        )

    return router