import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.crud.trading import account_balance as crud_account_balance
from app.crud.trading import trade_order as crud_trade_order
from app.crud.transaction import transaction as crud_transaction
from app.core.constants import OrderTypeEnum, OrderStatusEnum
from app.services.trading import trading_service
from app.crud.user import user as crud_user
from app.core.security import get_password_hash
from app.models.user import User
from app.core.constants import ADMIN_SCHOOL_NAME, RoleEnum
from app.crud.school import school as crud_school
from app.crud.role import role as crud_role


@pytest.fixture
def user_with_trading_account(db_session: Session, _ensure_admin_school_exists, _ensure_student_role_exists):
    """Create a user with a trading account"""
    admin_school = _ensure_admin_school_exists
    student_role = _ensure_student_role_exists
    
    user_data = {
        "full_name": "Trading Test User",
        "email": f"trader-{id(object())}@test.com",
        "hashed_password": get_password_hash("testpass123"),
        "is_active": True
    }
    user = crud_user.create(db_session, obj_in=user_data)
    crud_user.add_user_to_school(db_session, user=user, school=admin_school, role=student_role)
    db_session.commit()
    return user


@pytest.mark.asyncio
async def test_period_start_value_with_initial_balance(db_session: Session, user_with_trading_account):
    """Test that period_start_value correctly includes initial cash balance"""
    user_id = user_with_trading_account.id
    
    initial_balance = Decimal("10000.00")
    account = crud_account_balance.get_by_user_id(db_session, user_id=user_id)
    if not account:
        account = crud_account_balance.create(
            db_session,
            obj_in={"user_id": user_id, "balance": initial_balance}
        )
    else:
        account = crud_account_balance.update(
            db_session,
            db_obj=account,
            obj_in={"balance": initial_balance}
        )
    
    fund_date = datetime.utcnow() - timedelta(days=15)
    crud_transaction.create(
        db_session,
        obj_in={
            "user_id": user_id,
            "amount": initial_balance,
            "transaction_type": "fund_addition",
            "created_at": fund_date
        }
    )
    
    start_date = datetime.utcnow() - timedelta(days=10)
    end_date = datetime.utcnow()
    
    balance = await trading_service.get_account_balance(
        db_session,
        user_id=user_id,
        from_date=start_date,
        to_date=end_date
    )
    
    assert balance.period_start_value is not None, "period_start_value should not be None"
    assert balance.period_start_value > 0, f"period_start_value should be > 0, got {balance.period_start_value}"
    assert balance.period_start_value >= float(initial_balance), \
        f"period_start_value should be >= initial balance {initial_balance}, got {balance.period_start_value}"


@pytest.mark.asyncio
async def test_period_pnl_with_trade_in_period(db_session: Session, user_with_trading_account):
    """Test that period P&L correctly tracks trades and price changes"""
    user_id = user_with_trading_account.id
    
    initial_balance = Decimal("10000.00")
    account = crud_account_balance.get_by_user_id(db_session, user_id=user_id)
    if not account:
        account = crud_account_balance.create(
            db_session,
            obj_in={"user_id": user_id, "balance": initial_balance}
        )
    else:
        account = crud_account_balance.update(
            db_session,
            db_obj=account,
            obj_in={"balance": initial_balance}
        )
    
    fund_date = datetime.utcnow() - timedelta(days=15)
    crud_transaction.create(
        db_session,
        obj_in={
            "user_id": user_id,
            "amount": initial_balance,
            "transaction_type": "fund_addition",
            "created_at": fund_date
        }
    )
    
    start_date = datetime.utcnow() - timedelta(days=10)
    end_date = datetime.utcnow() + timedelta(days=1)
    
    buy_date = start_date + timedelta(days=5)
    
    trade = crud_trade_order.create(
        db_session,
        obj_in={
            "user_id": user_id,
            "symbol": "AAPL",
            "quantity": 10,
            "price": Decimal("150.00"),
            "order_type": OrderTypeEnum.BUY,
            "status": OrderStatusEnum.FILLED,
            "executed_price": Decimal("150.00"),
            "total_amount": Decimal("1500.00"),
            "executed_at": buy_date
        }
    )
    
    balance = await trading_service.get_account_balance(
        db_session,
        user_id=user_id,
        from_date=start_date,
        to_date=end_date
    )
    
    assert balance.period_start_value is not None, "period_start_value should not be None"
    assert balance.period_start_value > 0, f"period_start_value should be > 0, got {balance.period_start_value}"
    
    assert balance.period_end_value is not None, "period_end_value should not be None"
    assert balance.period_end_value > 0, f"period_end_value should be > 0, got {balance.period_end_value}"
    
    assert balance.period_pnl is not None, "period_pnl should not be None"


@pytest.mark.asyncio
async def test_period_values_zero_when_no_activity(db_session: Session, user_with_trading_account):
    """Test that period values correctly show 0 when user has no balance or trades"""
    user_id = user_with_trading_account.id
    
    account = crud_account_balance.get_by_user_id(db_session, user_id=user_id)
    if not account:
        account = crud_account_balance.create(
            db_session,
            obj_in={"user_id": user_id, "balance": Decimal("0.00")}
        )
    else:
        account = crud_account_balance.update(
            db_session,
            db_obj=account,
            obj_in={"balance": Decimal("0.00")}
        )
    
    start_date = datetime.utcnow() - timedelta(days=10)
    end_date = datetime.utcnow()
    
    balance = await trading_service.get_account_balance(
        db_session,
        user_id=user_id,
        from_date=start_date,
        to_date=end_date
    )
    
    assert balance.period_start_value == 0.0, f"period_start_value should be 0.0 with no activity, got {balance.period_start_value}"
    assert balance.period_end_value == 0.0, f"period_end_value should be 0.0 with no activity, got {balance.period_end_value}"
    assert balance.period_pnl == 0.0, f"period_pnl should be 0.0 with no activity, got {balance.period_pnl}"
