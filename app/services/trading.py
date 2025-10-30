from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException, status
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from functools import wraps
from collections import defaultdict
import logging
import asyncio

from app.crud.user import user as user_crud
from app.crud.role import role as user_role
from app.schemas.trading import (
    PortfolioItemSchema,
    TradingAccountSummary,
    WatchlistStockSchema,
    UserWatchlistCreate,
    UserWatchlistUpdate,
    UserWatchlistSchema,
    AccountBalanceSchema,
    PortfolioPositionSchema,
    TradeOrderCreate,
    TradeOrder,
    PortfolioHistoricalDataPointSchema,
    OrderPreviewRequest,
    OrderPreview
)
from app.crud.trading import (
    user_watchlist as crud_user_watchlist,
    watchlist_stock as crud_watchlist_stock,
    account_balance as crud_account_balance,
    portfolio_position as crud_portfolio_position,
    trade_order as crud_trade_order
)
from app.crud.transaction import transaction as crud_transaction
from app.schemas.user import UserContext
from app.services.polygon import polygon_service
from app.core.constants import OrderTypeEnum, OrderStatusEnum, RoleEnum
from app.utils.permission import PermissionHelper as permission_helper

logger = logging.getLogger(__name__)

order_limits: Dict[int, List[datetime]] = defaultdict(list)

def rate_limit_orders(max_orders: int = 10, window_minutes: int = 1):
    def decorator(func):
        @wraps(func)
        async def wrapper(self, db: Session, user_id: int, *args, **kwargs):
            now = datetime.utcnow()

            order_limits[user_id] = [
                t for t in order_limits[user_id]
                if now - t < timedelta(minutes=window_minutes)
            ]

            if len(order_limits[user_id]) >= max_orders:
                logger.warning(f"Rate limit exceeded for user {user_id}")
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Too many orders. Maximum {max_orders} orders per {window_minutes} minute(s)."
                )

            order_limits[user_id].append(now)
            return await func(self, db, user_id, *args, **kwargs)
        return wrapper
    return decorator


class TradingService:

    async def create_user_watchlist(
        self,
        db: Session,
        user_id: int,
        watchlist_in: UserWatchlistCreate
    ) -> UserWatchlistSchema:
        existing = crud_user_watchlist.get_by_user_and_name(
            db, user_id=user_id, name=watchlist_in.name
        )

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Watchlist with this name already exists"
            )

        watchlist_data = watchlist_in.model_dump()
        watchlist_data["user_id"] = user_id

        new_watchlist = crud_user_watchlist.create(db, obj_in=watchlist_data)
        return UserWatchlistSchema.model_validate(new_watchlist)

    async def get_user_watchlists(
        self,
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[UserWatchlistSchema]:
        watchlists = crud_user_watchlist.get_multi_by_user(
            db, user_id=user_id, skip=skip, limit=limit
        )

        result_watchlists = []

        for wl in watchlists:
            stocks_with_sparkline = []
            symbols = [stock.symbol for stock in wl.stocks]

            sparkline_tasks = [
                polygon_service._get_sparkline_data(symbol)
                for symbol in symbols
            ]
            sparkline_results = await asyncio.gather(*sparkline_tasks, return_exceptions=True)

            for stock_item, sparkline_data in zip(wl.stocks, sparkline_results):
                if isinstance(sparkline_data, Exception):
                    logger.error(f"Error fetching sparkline for {stock_item.symbol}: {sparkline_data}")
                    sparkline_data = []

                stocks_with_sparkline.append(
                    WatchlistStockSchema.model_validate(
                        stock_item.__dict__ | {"sparkline_data": sparkline_data}
                    )
                )

            result_watchlists.append(
                UserWatchlistSchema.model_validate(
                    wl.__dict__ | {"stocks": stocks_with_sparkline}
                )
            )

        return result_watchlists

    async def get_user_watchlist_by_id(
        self,
        db: Session,
        user_id: int,
        watchlist_id: int
    ) -> UserWatchlistSchema:
        watchlist = crud_user_watchlist.get(db, id=watchlist_id)

        if not watchlist or watchlist.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Watchlist not found"
            )

        stocks_with_sparkline = []
        symbols = [stock.symbol for stock in watchlist.stocks]
        sparkline_tasks = [
            polygon_service._get_sparkline_data(symbol)
            for symbol in symbols
        ]
        sparkline_results = await asyncio.gather(*sparkline_tasks, return_exceptions=True)

        for stock_item, sparkline_data in zip(watchlist.stocks, sparkline_results):
            if isinstance(sparkline_data, Exception):
                logger.error(f"Error fetching sparkline for {stock_item.symbol}: {sparkline_data}")
                sparkline_data = []

            stocks_with_sparkline.append(
                WatchlistStockSchema.model_validate(
                    stock_item,
                    update={"sparkline_data": sparkline_data}
                )
            )

        return UserWatchlistSchema.model_validate(
            watchlist.__dict__ | {"stocks": stocks_with_sparkline}
        )

    async def update_user_watchlist(
        self,
        db: Session,
        user_id: int,
        watchlist_id: int,
        watchlist_in: UserWatchlistUpdate
    ) -> UserWatchlistSchema:
        watchlist = crud_user_watchlist.get(db, id=watchlist_id)

        if not watchlist or watchlist.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Watchlist not found"
            )

        if watchlist_in.name and watchlist_in.name != watchlist.name:
            existing = crud_user_watchlist.get_by_user_and_name(
                db, user_id=user_id, name=watchlist_in.name
            )
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Watchlist with this name already exists"
                )

        updated_watchlist = crud_user_watchlist.update(
            db, db_obj=watchlist, obj_in=watchlist_in
        )
        return UserWatchlistSchema.model_validate(updated_watchlist)

    def delete_user_watchlist(
        self,
        db: Session,
        user_id: int,
        watchlist_id: int
    ) -> dict:
        watchlist = crud_user_watchlist.get(db, id=watchlist_id)

        if not watchlist or watchlist.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Watchlist not found"
            )

        crud_user_watchlist.remove(db, id=watchlist_id)
        return {"message": "Watchlist deleted successfully"}

    async def add_stock_to_watchlist(
        self,
        db: Session,
        user_id: int,
        watchlist_id: int,
        symbol: str
    ) -> UserWatchlistSchema:
        watchlist = crud_user_watchlist.get(db, id=watchlist_id)

        if not watchlist or watchlist.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Watchlist not found"
            )

        existing = crud_watchlist_stock.get_by_watchlist_and_symbol(
            db, watchlist_id=watchlist_id, symbol=symbol.upper()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Stock already in watchlist"
            )

        try:
            quote = await polygon_service.get_latest_quote(symbol.upper())
            if not quote:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Stock symbol {symbol.upper()} not found"
                )
        except Exception as e:
            logger.error(f"Error validating symbol {symbol}: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid stock symbol: {symbol}"
            )

        crud_watchlist_stock.create(
            db,
            obj_in={"watchlist_id": watchlist_id, "symbol": symbol.upper()}
        )
        db.refresh(watchlist)

        stocks_with_sparkline = []
        symbols = [stock.symbol for stock in watchlist.stocks]
        sparkline_tasks = [
            polygon_service._get_sparkline_data(sym)
            for sym in symbols
        ]
        sparkline_results = await asyncio.gather(*sparkline_tasks, return_exceptions=True)

        for stock_item, sparkline_data in zip(watchlist.stocks, sparkline_results):
            if isinstance(sparkline_data, Exception):
                sparkline_data = []

            stocks_with_sparkline.append(
                WatchlistStockSchema.model_validate(
                    stock_item.__dict__ | {"sparkline_data": sparkline_data}
                )
            )

        return UserWatchlistSchema.model_validate(
            watchlist.__dict__ | {"stocks": stocks_with_sparkline}
        )

    async def remove_stock_from_watchlist(
        self,
        db: Session,
        user_id: int,
        watchlist_id: int,
        symbol: str
    ) -> UserWatchlistSchema:
        watchlist = crud_user_watchlist.get(db, id=watchlist_id)

        if not watchlist or watchlist.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Watchlist not found"
            )

        stock = crud_watchlist_stock.get_by_watchlist_and_symbol(
            db, watchlist_id=watchlist_id, symbol=symbol.upper()
        )
        if not stock:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Stock not in watchlist"
            )

        crud_watchlist_stock.remove(db, id=stock.id)
        db.refresh(watchlist)

        stocks_with_sparkline = []
        symbols = [s.symbol for s in watchlist.stocks]
        sparkline_tasks = [
            polygon_service._get_sparkline_data(sym)
            for sym in symbols
        ]
        sparkline_results = await asyncio.gather(*sparkline_tasks, return_exceptions=True)

        for stock_item, sparkline_data in zip(watchlist.stocks, sparkline_results):
            if isinstance(sparkline_data, Exception):
                sparkline_data = []

            stocks_with_sparkline.append(
                WatchlistStockSchema.model_validate(
                    stock_item.__dict__ | {"sparkline_data": sparkline_data}
                )
            )

        return UserWatchlistSchema.model_validate(
            watchlist.__dict__ | {"stocks": stocks_with_sparkline}
        )

    # ============ ACCOUNT BALANCE METHODS ============

    def get_account_balance(
        self,
        db: Session,
        user_id: int
    ) -> AccountBalanceSchema:
        account = crud_account_balance.get_by_user_id(db, user_id=user_id)

        if not account:
            account = crud_account_balance.create(
                db,
                obj_in={"user_id": user_id, "balance": Decimal("0.00")}
            )

        return AccountBalanceSchema.model_validate(account)

    async def add_funds_to_student_account(
        self,
        db: Session,
        student_id: int,
        amount: Decimal,
        current_user_context: UserContext
    ) -> AccountBalanceSchema:
        if permission_helper.is_student(current_user_context):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Students cannot add funds to accounts"
            )

        if not (permission_helper.is_super_admin(current_user_context) or
                permission_helper.is_school_admin(current_user_context) or
                permission_helper.is_teacher(current_user_context)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )

        student_user = user_crud.get(db, id=student_id)
        if not student_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found"
            )

        student_role = user_role.get_by_name(db, name=RoleEnum.STUDENT)
        if not student_role:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Student role not configured"
            )

        student_association = user_crud.get_association_by_user_school_role(
            db,
            user_id=student_id,
            school_id=current_user_context.school.id,
            role_id=student_role.id
        )
        if not student_association:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Student not in your school"
            )

        if amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Amount must be positive"
            )

        account = crud_account_balance.get_by_user_id(db, user_id=student_id)

        if not account:
            account = crud_account_balance.create(
                db,
                obj_in={"user_id": student_id, "balance": amount}
            )
        else:
            new_balance = Decimal(str(account.balance)) + amount
            account = crud_account_balance.update(
                db,
                db_obj=account,
                obj_in={"balance": new_balance}
            )

        logger.info(
            f"User {current_user_context.user.id} added ${amount} "
            f"to student {student_id}. New balance: ${account.balance}"
        )

        crud_transaction.create(
            db,
            obj_in={
                "user_id": student_id,
                "initiator_id": current_user_context.user.id,
                "amount": amount,
                "transaction_type": "fund_addition"
            }
        )

        return AccountBalanceSchema.model_validate(account)

    # ============ PORTFOLIO METHODS ============

    async def get_portfolio(
        self,
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[PortfolioPositionSchema]:
        positions = crud_portfolio_position.get_multi_by_user(
            db,
            user_id=user_id,
            skip=skip,
            limit=limit
        )

        return [PortfolioPositionSchema.model_validate(p) for p in positions]

    async def get_portfolio_position_by_id(
        self,
        db: Session,
        user_id: int,
        position_id: int
    ) -> PortfolioItemSchema:
        position = crud_portfolio_position.get(db, id=position_id)

        if not position or position.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Portfolio position not found"
            )

        detail = (await polygon_service.get_multi_stock_details([position.symbol])).get(position.symbol, {})
        current_price = Decimal(str(detail.get("price", 0.0)))

        cost_value = Decimal(str(position.quantity)) * Decimal(str(position.average_price))
        current_value = Decimal(str(position.quantity)) * current_price
        unrealized_profit_loss = current_value - cost_value
        unrealized_profit_loss_percent = (unrealized_profit_loss / cost_value * 100) if cost_value else Decimal("0.00")

        all_positions = crud_portfolio_position.get_multi_by_user(db, user_id=user_id)
        all_symbols = [p.symbol for p in all_positions]
        all_stock_details_map = await polygon_service.get_multi_stock_details(all_symbols)

        total_portfolio_market_value = Decimal("0.00")
        for p in all_positions:
            detail = all_stock_details_map.get(p.symbol, {})
            total_portfolio_market_value += Decimal(str(p.quantity)) * Decimal(str(detail.get("price", 0.0)))

        percentage_of_portfolio = (current_value / total_portfolio_market_value * 100) if total_portfolio_market_value else Decimal("0.00")

        return PortfolioItemSchema(
            id=position.id,
            user_id=position.user_id,
            symbol=position.symbol,
            quantity=position.quantity,
            average_price=float(position.average_price),
            cost_value=float(cost_value),
            current_price=float(current_price),
            current_value=float(current_value),
            unrealized_profit_loss=float(unrealized_profit_loss),
            unrealized_profit_loss_percent=float(unrealized_profit_loss_percent),
            percentage_of_portfolio=float(percentage_of_portfolio),
            created_at=position.created_at,
            updated_at=position.updated_at
        )

    # ============ TRADING METHODS ============

    @rate_limit_orders(max_orders=10, window_minutes=1)
    async def place_order(
        self,
        db: Session,
        user_id: int,
        order_in: TradeOrderCreate
    ) -> TradeOrder:
        account = crud_account_balance.get_by_user_id(db, user_id=user_id)
        if not account:
            account = crud_account_balance.create(
                db,
                obj_in={"user_id": user_id, "balance": Decimal("0.00")}
            )

        if order_in.quantity <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quantity must be greater than 0"
            )

        quote = await polygon_service.get_latest_quote(order_in.symbol.upper())
        if not quote or not quote.get('price'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not get price for {order_in.symbol}"
            )

        current_price = Decimal(str(quote['price']))
        if current_price <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid stock price"
            )

        executed_price = current_price
        total_amount = (Decimal(str(order_in.quantity)) * executed_price).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )

        if order_in.order_type == OrderTypeEnum.BUY:
            await self._process_buy_order(
                db, user_id, order_in, account, executed_price, total_amount
            )
        elif order_in.order_type == OrderTypeEnum.SELL:
            await self._process_sell_order(
                db, user_id, order_in, account, executed_price, total_amount
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid order type"
            )

        trade_data = order_in.model_dump()
        trade_data.update({
            "user_id": user_id,
            "symbol": order_in.symbol.upper(),
            "status": OrderStatusEnum.FILLED,
            "executed_price": executed_price,
            "total_amount": total_amount,
            "executed_at": datetime.utcnow()
        })

        new_trade = crud_trade_order.create(db, obj_in=trade_data)

        logger.info(
            f"Order placed: user={user_id}, symbol={order_in.symbol}, "
            f"type={order_in.order_type}, qty={order_in.quantity}, price={executed_price}"
        )

        return TradeOrder.model_validate(new_trade)

    async def _process_buy_order(
        self,
        db: Session,
        user_id: int,
        order_in: TradeOrderCreate,
        account,
        executed_price: Decimal,
        total_amount: Decimal
    ):
        if Decimal(str(account.balance)) < total_amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient funds. Required: ${total_amount:.2f}, "
                       f"Available: ${account.balance:.2f}"
            )

        new_balance = Decimal(str(account.balance)) - total_amount
        crud_account_balance.update(
            db,
            db_obj=account,
            obj_in={"balance": new_balance}
        )

        position = crud_portfolio_position.get_by_user_and_symbol(
            db,
            user_id=user_id,
            symbol=order_in.symbol.upper()
        )

        if position:
            total_cost = (
                Decimal(str(position.quantity)) * Decimal(str(position.average_price))
            ) + total_amount
            total_quantity = Decimal(str(position.quantity)) + Decimal(str(order_in.quantity))
            new_avg_price = (total_cost / total_quantity).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )

            crud_portfolio_position.update(
                db,
                db_obj=position,
                obj_in={
                    "quantity": int(total_quantity),
                    "average_price": new_avg_price
                }
            )
        else:
            crud_portfolio_position.create(
                db,
                obj_in={
                    "user_id": user_id,
                    "symbol": order_in.symbol.upper(),
                    "quantity": order_in.quantity,
                    "average_price": executed_price
                }
            )

    async def _process_sell_order(
        self,
        db: Session,
        user_id: int,
        order_in: TradeOrderCreate,
        account,
        executed_price: Decimal,
        total_amount: Decimal
    ):
        position = crud_portfolio_position.get_by_user_and_symbol(
            db,
            user_id=user_id,
            symbol=order_in.symbol.upper()
        )

        if not position:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"You don't own any shares of {order_in.symbol}"
            )

        if position.quantity < order_in.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient shares. You own {position.quantity}, "
                       f"trying to sell {order_in.quantity}"
            )

        new_balance = Decimal(str(account.balance)) + total_amount
        crud_account_balance.update(
            db,
            db_obj=account,
            obj_in={"balance": new_balance}
        )

        new_quantity = position.quantity - order_in.quantity

        if new_quantity == 0:
            crud_portfolio_position.delete(db, id=position.id)
        else:
            crud_portfolio_position.update(
                db,
                db_obj=position,
                obj_in={"quantity": new_quantity}
            )

    async def preview_order(
        self,
        db: Session,
        user_id: int,
        order_preview: OrderPreviewRequest
    ) -> OrderPreview:
        quote = await polygon_service.get_latest_quote(order_preview.symbol.upper())

        if not quote or not quote.get('price'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not get price for {order_preview.symbol}"
            )

        current_price = Decimal(str(quote['price']))

        if order_preview.sell_in_dollars and order_preview.order_type == OrderTypeEnum.SELL:
            quantity = (Decimal(str(order_preview.amount)) / current_price).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
        else:
            quantity = Decimal(str(order_preview.quantity))

        estimated_total = (quantity * current_price).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )

        return OrderPreview(
            market_price=float(current_price),
            quantity=float(quantity),
            estimated_total=float(estimated_total),
            order_type=order_preview.order_type
        )

    def get_trade_history(
        self,
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[TradeOrder]:
        trades = crud_trade_order.get_multi_by_user(
            db,
            user_id=user_id,
            skip=skip,
            limit=limit
        )

        return [TradeOrder.model_validate(t) for t in trades]

    async def get_portfolio_historical_data(
        self,
        db: Session,
        user_id: int,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> List[PortfolioHistoricalDataPointSchema]:
        all_trades = crud_trade_order.get_multi_by_user(db, user_id=user_id)

        if not all_trades:
            return []

        earliest_trade_date = min(trade.executed_at.date() for trade in all_trades)

        start_date = from_date.date() if from_date else earliest_trade_date
        end_date = to_date.date() if to_date else datetime.utcnow().date()

        if start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="from_date must be before to_date"
            )

        current_holdings = defaultdict(Decimal)
        initial_trades = [t for t in all_trades if t.executed_at.date() < start_date]

        for trade in initial_trades:
            qty = Decimal(str(trade.quantity))
            if trade.order_type == OrderTypeEnum.BUY:
                current_holdings[trade.symbol] += qty
            elif trade.order_type == OrderTypeEnum.SELL:
                current_holdings[trade.symbol] -= qty

        current_holdings = {s: q for s, q in current_holdings.items() if q > 0}

        relevant_trades = [
            t for t in all_trades
            if start_date <= t.executed_at.date() <= end_date
        ]
        relevant_trades.sort(key=lambda x: x.executed_at)

        trades_by_date = defaultdict(list)
        for trade in relevant_trades:
            trades_by_date[trade.executed_at.date()].append(trade)

        historical_data = []
        current_date = start_date

        while current_date <= end_date:
            for trade in trades_by_date.get(current_date, []):
                qty = Decimal(str(trade.quantity))

                if trade.order_type == OrderTypeEnum.BUY:
                    current_holdings[trade.symbol] = current_holdings.get(trade.symbol, Decimal('0')) + qty
                elif trade.order_type == OrderTypeEnum.SELL:
                    current_holdings[trade.symbol] = current_holdings.get(trade.symbol, Decimal('0')) - qty
                    if current_holdings[trade.symbol] <= 0:
                        current_holdings.pop(trade.symbol, None)

            total_value = Decimal('0.00')

            if current_holdings:
                symbols = list(current_holdings.keys())

                price_tasks = [
                    self._get_historical_price(symbol, current_date)
                    for symbol in symbols
                ]
                prices = await asyncio.gather(*price_tasks, return_exceptions=True)

                for symbol, price in zip(symbols, prices):
                    if isinstance(price, Exception):
                        logger.error(f"Error fetching price for {symbol} on {current_date}: {price}")
                        price = Decimal('0.00')
                    else:
                        price = Decimal(str(price))

                    total_value += current_holdings[symbol] * price

            historical_data.append(
                PortfolioHistoricalDataPointSchema(
                    timestamp=current_date,
                    total_value=float(total_value.quantize(
                        Decimal('0.01'), rounding=ROUND_HALF_UP
                    ))
                )
            )

            current_date += timedelta(days=1)

        return historical_data

    async def _get_historical_price(
        self,
        symbol: str,
        date: datetime
    ) -> float:
        try:
            historical_data = await polygon_service.get_historical_data(
                symbol,
                date,
                date,
                multiplier=1,
                timespan="day"
            )

            if historical_data and historical_data.get("results"):
                return float(historical_data["results"][0]["close"])

            latest_quote = await polygon_service.get_latest_quote(symbol)
            if latest_quote and latest_quote.get("price"):
                return float(latest_quote["price"])

            return 0.0

        except Exception as e:
            logger.error(f"Error fetching historical price for {symbol}: {e}")
            return 0.0

    async def get_trading_account_summary(
        self,
        db: Session,
        user_id: int
    ) -> TradingAccountSummary:
        fund_additions = crud_transaction.get_multi_by_user_and_type(
            db, user_id=user_id, transaction_type="fund_addition"
        )

        starting_capital = Decimal("0.00")
        total_funds_added = Decimal("0.00")
        if fund_additions:
            fund_additions.sort(key=lambda t: t.created_at)
            starting_capital = Decimal(str(fund_additions[0].amount))
            total_funds_added = sum(Decimal(str(t.amount)) for t in fund_additions[1:])

        account_balance = self.get_account_balance(db, user_id=user_id)
        current_cash_balance = Decimal(str(account_balance.balance))

        positions = crud_portfolio_position.get_multi_by_user(db, user_id=user_id)
        total_stock_value = Decimal("0.00")

        if positions:
            symbols = [p.symbol for p in positions]
            price_tasks = [polygon_service.get_latest_quote(s) for s in symbols]
            price_results = await asyncio.gather(*price_tasks, return_exceptions=True)

            for pos, quote_result in zip(positions, price_results):
                if isinstance(quote_result, Exception) or not quote_result or not quote_result.get('price'):
                    logger.error(f"Could not fetch price for {pos.symbol}. Using average cost.")
                    price = Decimal(str(pos.average_price))
                else:
                    price = Decimal(str(quote_result['price']))

                total_stock_value += Decimal(str(pos.quantity)) * price

        total_portfolio_value = current_cash_balance + total_stock_value
        total_invested = starting_capital + total_funds_added
        net_pl = total_portfolio_value - total_invested
        trading_profit = max(Decimal("0.00"), net_pl)
        trading_loss = abs(min(Decimal("0.00"), net_pl))

        return TradingAccountSummary(
            starting_capital=float(starting_capital),
            current_balance=float(current_cash_balance),
            trading_profit=float(trading_profit),
            trading_loss=float(trading_loss)
        )

trading_service = TradingService()