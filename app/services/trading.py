import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from functools import wraps
from typing import Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.cache import cache
from app.core.constants import OrderTypeEnum, OrderStatusEnum, RoleEnum
from app.crud.trading import (
    account_balance as crud_account_balance,
    portfolio_position as crud_portfolio_position,
    trade_order as crud_trade_order,
    user_watchlist as crud_user_watchlist,
    watchlist_stock as crud_watchlist_stock,
)
from app.crud.transaction import transaction as crud_transaction
from app.crud.user import user as user_crud
from app.crud.role import role as user_role
from app.schemas.trading import (
    AccountBalanceSchema,
    OrderPreview,
    OrderPreviewRequest,
    PortfolioHistoricalDataPointSchema,
    PortfolioItemSchema,
    PortfolioPositionSchema,
    TradeOrder,
    TradeOrderCreate,
    TradingAccountSummary,
    UserWatchlistCreate,
    UserWatchlistSchema,
    UserWatchlistUpdate,
    WatchlistStockSchema,
)
from app.schemas.user import UserContext
from app.services.logo import logo_service
from app.services.polygon import polygon_service
from app.utils.events import event_bus
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
            stocks_with_data = []
            symbols = [stock.symbol for stock in wl.stocks]

            sparkline_tasks = [
                polygon_service._get_sparkline_data(symbol)
                for symbol in symbols
            ]
            sparkline_results = await asyncio.gather(*sparkline_tasks, return_exceptions=True)

            company_details = await polygon_service.get_multi_stock_details(symbols)
            symbols_and_names = {symbol: company_details.get(symbol, {}).get("name") for symbol in symbols}
            logos = await logo_service.get_multiple_logos(symbols_and_names)

            for stock_item, sparkline_data in zip(wl.stocks, sparkline_results):
                if isinstance(sparkline_data, Exception):
                    logger.error(f"Error fetching sparkline for {stock_item.symbol}: {sparkline_data}")
                    sparkline_data = []

                stock_data = stock_item.__dict__ | {
                    "sparkline_data": sparkline_data,
                    "logo_url": logos.get(stock_item.symbol)
                }

                stocks_with_data.append(
                    WatchlistStockSchema.model_validate(stock_data)
                )

            result_watchlists.append(
                UserWatchlistSchema.model_validate(
                    wl.__dict__ | {"stocks": stocks_with_data}
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

        stocks_with_data = []
        symbols = [stock.symbol for stock in watchlist.stocks]

        sparkline_tasks = [
            polygon_service._get_sparkline_data(symbol)
            for symbol in symbols
        ]
        sparkline_results = await asyncio.gather(*sparkline_tasks, return_exceptions=True)

        company_details = await polygon_service.get_multi_stock_details(symbols)
        symbols_and_names = {symbol: company_details.get(symbol, {}).get("name") for symbol in symbols}
        logos = await logo_service.get_multiple_logos(symbols_and_names)

        for stock_item, sparkline_data in zip(watchlist.stocks, sparkline_results):
            if isinstance(sparkline_data, Exception):
                logger.error(f"Error fetching sparkline for {stock_item.symbol}: {sparkline_data}")
                sparkline_data = []

            stock_data = stock_item.__dict__ | {
                "sparkline_data": sparkline_data,
                "logo_url": logos.get(stock_item.symbol)
            }

            stocks_with_data.append(
                WatchlistStockSchema.model_validate(stock_data)
            )

        return UserWatchlistSchema.model_validate(
            watchlist.__dict__ | {"stocks": stocks_with_data}
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

    async def delete_user_watchlist(
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

        crud_user_watchlist.delete(db, id=watchlist_id)
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

        crud_watchlist_stock.delete(db, id=stock.id)
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

    async def get_account_balance(
        self,
        db: Session,
        user_id: int,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> AccountBalanceSchema:
        account = crud_account_balance.get_by_user_id(db, user_id=user_id)

        if not account:
            account = crud_account_balance.create(
                db,
                obj_in={"user_id": user_id, "balance": Decimal("0.00")}
            )

        available_balance = Decimal(str(account.balance))
        amount_invested = Decimal("0.00")
        total_amount = Decimal("0.00")

        positions = crud_portfolio_position.get_multi_by_user(db, user_id=user_id)

        for pos in positions:
            cost_basis = Decimal(str(pos.quantity)) * Decimal(str(pos.average_price))
            amount_invested += cost_basis

        portfolio_value = Decimal("0.00")
        if positions:
            symbols = [p.symbol for p in positions]
            price_tasks = [polygon_service.get_latest_quote(s) for s in symbols]
            price_results = await asyncio.gather(*price_tasks, return_exceptions=True)

            for pos, quote_result in zip(positions, price_results):
                if isinstance(quote_result, Exception) or not quote_result or not quote_result.get('price'):
                    logger.warning(f"Could not fetch price for {pos.symbol}. Skipping from portfolio value calculation.")
                    continue

                current_price = Decimal(str(quote_result['price']))
                portfolio_value += Decimal(str(pos.quantity)) * current_price

        total_amount = available_balance + amount_invested

        period_pnl = None
        period_start_value = None
        period_end_value = None
        period_start_date = from_date
        period_end_date = to_date

        if from_date and to_date:
            try:
                period_pnl_data = await self._calculate_period_portfolio_pnl(
                    db, user_id, from_date, to_date
                )
                period_pnl = period_pnl_data.get('period_pnl')
                period_start_value = period_pnl_data.get('start_value')
                period_end_value = period_pnl_data.get('end_value')
            except Exception as e:
                logger.error(f"Error calculating period P&L for user {user_id}: {e}")

        return AccountBalanceSchema(
            id=account.id,
            user_id=user_id,
            balance=float(available_balance),
            available_balance=float(available_balance),
            amount_invested=float(amount_invested),
            total_amount=float(total_amount),
            period_pnl=period_pnl,
            period_start_value=period_start_value,
            period_end_value=period_end_value,
            period_start_date=period_start_date,
            period_end_date=period_end_date,
            created_at=account.created_at,
            updated_at=account.updated_at
        )

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

        await event_bus.publish("trade_executed", {
            "student_id": user_id,
            "symbol": order_in.symbol,
            "quantity": order_in.quantity,
            "executed_price": float(executed_price),
            "total_amount": float(total_amount)
        })

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

    async def get_trade_history(
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

    async def _calculate_period_portfolio_pnl(
        self,
        db: Session,
        user_id: int,
        from_date: datetime,
        to_date: datetime
    ) -> dict:
        """Calculate portfolio P&L between two dates, adjusted for cash flows during the period"""
        all_trades = crud_trade_order.get_multi_by_user(db, user_id=user_id)

        if not all_trades:
            return {"period_pnl": 0.0, "start_value": 0.0, "end_value": 0.0}

        if from_date >= to_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="from_date must be before to_date"
            )

        start_date = from_date.date()
        end_date = to_date.date()

        start_holdings = self._calculate_holdings_at_date(all_trades, start_date)
        start_portfolio_value = await self._calculate_portfolio_value_at_date(start_holdings, start_date)
        start_cash_balance = self._calculate_cash_balance_at_date(db, user_id, all_trades, start_date)
        start_value = start_portfolio_value + start_cash_balance

        end_holdings = self._calculate_holdings_at_date(all_trades, end_date)
        end_portfolio_value = await self._calculate_portfolio_value_at_date(end_holdings, end_date)
        end_cash_balance = self._calculate_cash_balance_at_date(db, user_id, all_trades, end_date)
        end_value = end_portfolio_value + end_cash_balance

        cash_flows = crud_transaction.get_multi_by_user_in_date_range(
            db, user_id=user_id, from_date=from_date, to_date=to_date
        )
        total_cash_inflows = sum(Decimal(str(t.amount)) for t in cash_flows if Decimal(str(t.amount)) > 0)
        total_cash_outflows = sum(abs(Decimal(str(t.amount))) for t in cash_flows if Decimal(str(t.amount)) < 0)

        net_cash_flow = total_cash_inflows - total_cash_outflows

        period_pnl = float(end_value - start_value - net_cash_flow)

        return {
            "period_pnl": period_pnl,
            "start_value": float(start_value),
            "end_value": float(end_value)
        }

    def _calculate_cash_balance_at_date(
        self,
        db: Session,
        user_id: int,
        all_trades: list,
        target_date: datetime.date
    ) -> Decimal:
        """Calculate cash balance at a specific date by replaying transactions"""
        cash_balance = Decimal("0.00")

        # Add all fund additions up to target date
        fund_additions = crud_transaction.get_multi_by_user_and_type_up_to_date(
            db, user_id=user_id, transaction_type="fund_addition", up_to_date=target_date
        )
        for transaction in fund_additions:
            cash_balance += Decimal(str(transaction.amount))

        # Adjust for trades up to target date
        relevant_trades = [
            t for t in all_trades
            if t.executed_at.date() <= target_date and t.status == OrderStatusEnum.FILLED
        ]

        for trade in relevant_trades:
            total_amount = Decimal(str(trade.total_amount))
            if trade.order_type == OrderTypeEnum.BUY:
                cash_balance -= total_amount
            elif trade.order_type == OrderTypeEnum.SELL:
                cash_balance += total_amount

        return cash_balance

    def _calculate_holdings_at_date(
        self,
        all_trades: list,
        target_date: datetime.date
    ) -> dict:
        """Calculate what holdings the user had at a specific date"""
        holdings = defaultdict(Decimal)

        # Get all trades up to and including target date
        relevant_trades = [
            t for t in all_trades
            if t.executed_at.date() <= target_date and t.status == OrderStatusEnum.FILLED
        ]
        relevant_trades.sort(key=lambda x: x.executed_at)

        # Replay trades to calculate holdings
        for trade in relevant_trades:
            qty = Decimal(str(trade.quantity))
            if trade.order_type == OrderTypeEnum.BUY:
                holdings[trade.symbol] += qty
            elif trade.order_type == OrderTypeEnum.SELL:
                holdings[trade.symbol] -= qty
                if holdings[trade.symbol] <= 0:
                    holdings.pop(trade.symbol, None)

        return dict(holdings)

    async def _calculate_portfolio_value_at_date(
        self,
        holdings: dict,
        target_date: datetime
    ) -> Decimal:
        """Calculate total portfolio value for given holdings on a specific date"""
        if not holdings:
            return Decimal("0.00")

        symbols = list(holdings.keys())
        price_tasks = [
            self._get_historical_price(symbol, target_date)
            for symbol in symbols
        ]
        prices = await asyncio.gather(*price_tasks, return_exceptions=True)

        total_value = Decimal("0.00")
        for symbol, price in zip(symbols, prices):
            if isinstance(price, Exception):
                logger.warning(f"Could not get price for {symbol} on {target_date}, using 0")
                price = Decimal("0.00")
            else:
                price = Decimal(str(price))

            total_value += holdings[symbol] * price

        return total_value

    async def get_trading_account_summary(
        self,
        db: Session,
        user_id: int
    ) -> TradingAccountSummary:
        cache_key = f"trading_summary_{user_id}"
        cached = await cache.get(cache_key)
        if cached:
            return cached

        fund_additions = crud_transaction.get_multi_by_user_and_type(
            db, user_id=user_id, transaction_type="fund_addition"
        )

        starting_capital = Decimal("0.00")
        total_funds_added = Decimal("0.00")
        if fund_additions:
            fund_additions.sort(key=lambda t: t.created_at)
            starting_capital = Decimal(str(fund_additions[0].amount))
            total_funds_added = sum(Decimal(str(t.amount)) for t in fund_additions[1:])

        account_balance = await self.get_account_balance(db, user_id=user_id)
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

        result = TradingAccountSummary(
            starting_capital=float(starting_capital),
            current_balance=float(current_cash_balance),
            trading_profit=float(trading_profit),
            trading_loss=float(trading_loss)
        )

        await cache.set(cache_key, result, 300)
        return result

trading_service = TradingService()
