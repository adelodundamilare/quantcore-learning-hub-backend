from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException, status
from typing import List, Dict
from datetime import datetime, timedelta
from decimal import Decimal
from functools import wraps
from collections import defaultdict
import logging
from app.crud.user import user as user_crud
from app.crud.role import role as user_role

from app.schemas.trading import (
    WatchlistItemCreate,
    WatchlistItem,
    AccountBalanceSchema,
    PortfolioPositionSchema,
    TradeOrderCreate,
    TradeOrder
)
from app.crud.trading import (
    watchlist_item as crud_watchlist_item,
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
                    detail=f"Too many orders. Maximum {max_orders} orders per {window_minutes} minute(s). Try again later."
                )

            order_limits[user_id].append(now)
            return await func(self, db, user_id, *args, **kwargs)
        return wrapper
    return decorator

class TradingService:
    def add_stock_to_watchlist(
        self,
        db: Session,
        user_id: int,
        watchlist_item_in: WatchlistItemCreate
    ) -> WatchlistItem:
        existing_item = crud_watchlist_item.get_by_user_and_symbol(
            db,
            user_id=user_id,
            symbol=watchlist_item_in.symbol
        )

        if existing_item:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Stock already in watchlist."
            )

        new_item_data = watchlist_item_in.model_dump()
        new_item_data["user_id"] = user_id

        return crud_watchlist_item.create(db, obj_in=new_item_data)

    def remove_stock_from_watchlist(
        self,
        db: Session,
        user_id: int,
        symbol: str
    ) -> WatchlistItem:
        existing_item = crud_watchlist_item.get_by_user_and_symbol(
            db,
            user_id=user_id,
            symbol=symbol
        )

        if not existing_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Stock not found in watchlist."
            )

        crud_watchlist_item.delete(db, id=existing_item.id)
        return existing_item

    async def get_user_watchlist(
        self,
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[WatchlistItem]:
        watchlist_items = crud_watchlist_item.get_multi_by_user(
            db,
            user_id=user_id,
            skip=skip,
            limit=limit
        )

        for item in watchlist_items:
            item.sparkline_data = await polygon_service._get_sparkline_data(item.symbol)

        return [WatchlistItem.model_validate(item) for item in watchlist_items]

    def get_account_balance(
        self,
        db: Session,
        user_id: int
    ) -> AccountBalanceSchema:
        account = crud_account_balance.get_by_user_id(db, user_id=user_id)

        if not account:
            account = crud_account_balance.create(
                db,
                obj_in={
                    "user_id": user_id,
                    "balance": 0.00
                }
            )

        return AccountBalanceSchema.model_validate(account)

    async def add_funds_to_student_account(
        self,
        db: Session,
        student_id: int,
        amount: float,
        current_user_context: UserContext
    ) -> AccountBalanceSchema:
        if permission_helper.is_student(current_user_context):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Students cannot add funds to other accounts."
            )

        if not (permission_helper.is_super_admin(current_user_context) or
                permission_helper.is_school_admin(current_user_context) or
                permission_helper.is_teacher(current_user_context)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to add funds to student accounts."
            )

        student_user = user_crud.get(db, id=student_id)
        if not student_user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")

        student_role = user_role.get_by_name(db, name=RoleEnum.STUDENT)
        if not student_role:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Student role not found.")

        student_association = user_crud.get_association_by_user_school_role(
            db, user_id=student_id, school_id=current_user_context.school.id, role_id=student_role.id
        )
        if not student_association:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Target user is not a student in your school."
            )

        if amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Amount must be positive."
            )

        account = crud_account_balance.get_by_user_id(db, user_id=student_id)

        if not account:
            account = crud_account_balance.create(
                db,
                obj_in={
                    "user_id": student_id,
                    "balance": amount
                }
            )
        else:
            updated_balance = account.balance + amount
            account = crud_account_balance.update(
                db,
                db_obj=account,
                obj_in={"balance": updated_balance}
            )

        logger.info(f"User {current_user_context.user.id} added {amount} to student {student_id}'s account. New balance: {account.balance}")

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

    def get_portfolio(
        self,
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[PortfolioPositionSchema]:
        portfolio = crud_portfolio_position.get_multi_by_user(
            db,
            user_id=user_id,
            skip=skip,
            limit=limit
        )

        return [PortfolioPositionSchema.model_validate(p) for p in portfolio]

    @rate_limit_orders(max_orders=10, window_minutes=1)
    async def place_order(
        self,
        db: Session,
        user_id: int,
        order_in: TradeOrderCreate
    ) -> TradeOrder:
        try:
            account = crud_account_balance.get_by_user_id(db, user_id=user_id)

            if not account:
                account = crud_account_balance.create(
                    db,
                    obj_in={
                        "user_id": user_id,
                        "balance": 0.00
                    }
                )

            if order_in.quantity <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Quantity must be greater than 0"
                )

            quote = await polygon_service.get_latest_quote(order_in.symbol)

            if not quote or not quote.get('p'):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Could not get current price for {order_in.symbol}"
                )

            current_price = float(quote['p'])

            if current_price <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid stock price"
                )

            executed_price = current_price
            total_amount = round(order_in.quantity * executed_price, 2)

            if order_in.order_type == OrderTypeEnum.BUY:
                if account.balance < total_amount:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Insufficient funds. Required: ${total_amount:.2f}, Available: ${account.balance:.2f}"
                    )

                account.balance = round(account.balance - total_amount, 2)
                crud_account_balance.update(
                    db,
                    db_obj=account,
                    obj_in={"balance": account.balance}
                )

                position = crud_portfolio_position.get_by_user_and_symbol(
                    db,
                    user_id=user_id,
                    symbol=order_in.symbol
                )

                if position:
                    total_cost = (position.quantity * position.average_price) + total_amount
                    total_quantity = position.quantity + order_in.quantity
                    new_avg_price = round(total_cost / total_quantity, 2)

                    crud_portfolio_position.update(
                        db,
                        db_obj=position,
                        obj_in={
                            "quantity": total_quantity,
                            "average_price": new_avg_price
                        }
                    )
                else:
                    crud_portfolio_position.create(
                        db,
                        obj_in={
                            "user_id": user_id,
                            "symbol": order_in.symbol,
                            "quantity": order_in.quantity,
                            "average_price": executed_price
                        }
                    )

            elif order_in.order_type == OrderTypeEnum.SELL:
                position = crud_portfolio_position.get_by_user_and_symbol(
                    db,
                    user_id=user_id,
                    symbol=order_in.symbol
                )

                if not position:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"You don't own any shares of {order_in.symbol}"
                    )

                if position.quantity < order_in.quantity:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Insufficient shares. You own {position.quantity}, trying to sell {order_in.quantity}"
                    )

                account.balance = round(account.balance + total_amount, 2)
                crud_account_balance.update(
                    db,
                    db_obj=account,
                    obj_in={"balance": account.balance}
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

            trade_data = order_in.model_dump()
            trade_data.update({
                "user_id": user_id,
                "status": OrderStatusEnum.FILLED,
                "executed_price": executed_price,
                "total_amount": total_amount,
                "executed_at": datetime.utcnow()
            })

            new_trade = crud_trade_order.create(db, obj_in=trade_data)

            db.commit()

            return TradeOrder.model_validate(new_trade)

        except HTTPException:
            db.rollback()
            raise
        except SQLAlchemyError as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error: {str(e)}"
            )
        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error processing order: {str(e)}"
            )

    def get_trade_history(
        self,
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[TradeOrder]:
        history = crud_trade_order.get_multi_by_user(
            db,
            user_id=user_id,
            skip=skip,
            limit=limit
        )

        return [TradeOrder.model_validate(t) for t in history]

trading_service = TradingService()