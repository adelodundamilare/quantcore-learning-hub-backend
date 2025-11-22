import pytest
import uuid
from sqlalchemy.orm import Session
from app.core.constants import OrderTypeEnum
from app.services.trading import trading_service
from app.services.polygon import polygon_service
from app.crud.trading import portfolio_position, trade_order, account_balance
from app.core.cache import cache
from app.core.cache_config import CACHE_KEYS
from app.schemas.trading import TradeOrderCreate
import asyncio


@pytest.mark.asyncio
async def test_trading_operations_invalidate_cache(db_session: Session, user_factory):
    """Test that trading operations properly invalidate cache"""
    student = user_factory("test-trading@example.com")

    account = account_balance.create(db_session, obj_in={
        "user_id": student.id,
        "balance": 10000.00
    })

    quote = await polygon_service.get_latest_quote("AAPL")
    assert quote and quote.get('price'), "Failed to get AAPL quote"

    current_price = float(quote['price'])

    buy_order = await trading_service.place_order(db_session, student.id, TradeOrderCreate(
        symbol="AAPL",
        quantity=10,
        order_type=OrderTypeEnum.BUY,
        price=current_price
    ))

    assert buy_order is not None, "Buy order failed"

    position = portfolio_position.get_by_user_and_symbol(db_session, student.id, "AAPL")
    assert position is not None, "Position not created"
    assert position.quantity == 10, f"Expected 10 shares, got {position.quantity}"

    await cache.delete_pattern("portfolio:*")
    await cache.delete_pattern("trades:*")
    await cache.delete_pattern("balance:user:*")
    await cache.delete_pattern("trading_summary_*")

    portfolio1 = await trading_service.get_portfolio(db_session, student.id)
    assert len(portfolio1) >= 1, "Portfolio should have position"
    assert portfolio1[0].symbol == "AAPL", "Should have AAPL position"

    portfolio2 = await trading_service.get_portfolio(db_session, student.id)
    assert portfolio2 == portfolio1, "Portfolio data should be identical"

    sell_order = await trading_service.place_order(db_session, student.id, TradeOrderCreate(
        symbol="AAPL",
        quantity=5,
        order_type=OrderTypeEnum.SELL,
        price=current_price
    ))

    assert sell_order is not None, "Sell order failed"

    updated_position = portfolio_position.get_by_user_and_symbol(db_session, student.id, "AAPL")
    assert updated_position.quantity == 5, f"Expected 5 shares remaining, got {updated_position.quantity}"

    portfolio3 = await trading_service.get_portfolio(db_session, student.id)
    aapl_position = next((p for p in portfolio3 if p.symbol == "AAPL"), None)
    assert aapl_position is not None, "AAPL position should still exist"
    assert aapl_position.quantity == 5, f"Portfolio should show 5 shares, got {aapl_position.quantity}"

    await cache.delete_pattern("portfolio:user:{}:*".format(student.id))


@pytest.mark.asyncio
async def test_sell_validation_with_owned_shares(db_session: Session, user_factory):
    """Test that users can sell shares they actually own"""
    student = user_factory("test-sell-owned@example.com")

    account = account_balance.create(db_session, obj_in={
        "user_id": student.id,
        "balance": 10000.00
    })

    quote = await polygon_service.get_latest_quote("AAPL")
    assert quote and quote.get('price'), "Failed to get AAPL quote"

    current_price = float(quote['price'])

    buy_order = await trading_service.place_order(db_session, student.id, TradeOrderCreate(
        symbol="AAPL",
        quantity=10,
        order_type=OrderTypeEnum.BUY,
        price=current_price
    ))

    assert buy_order is not None, "Buy order failed"

    position = portfolio_position.get_by_user_and_symbol(db_session, student.id, "AAPL")
    assert position is not None, "Position not created"
    assert position.quantity == 10, f"Expected 10 shares, got {position.quantity}"

    sell_order = await trading_service.place_order(db_session, student.id, TradeOrderCreate(
        symbol="AAPL",
        quantity=5,
        order_type=OrderTypeEnum.SELL,
        price=current_price
    ))

    assert sell_order is not None, "Sell order should succeed for owned shares"

    updated_position = portfolio_position.get_by_user_and_symbol(db_session, student.id, "AAPL")
    assert updated_position.quantity == 5, f"Expected 5 shares remaining, got {updated_position.quantity}"


@pytest.mark.asyncio
async def test_sell_validation_without_owned_shares(db_session: Session, user_factory):
    """Test that users cannot sell shares they don't own"""
    student = user_factory("test-no-shares@example.com")

    account = account_balance.create(db_session, obj_in={
        "user_id": student.id,
        "balance": 1000.00
    })

    with pytest.raises(Exception) as exc_info:
        await trading_service.place_order(db_session, student.id, TradeOrderCreate(
            symbol="AAPL",
            quantity=5,
            order_type=OrderTypeEnum.SELL,
            price=150.0
        ))

    assert "You don't own any shares of AAPL" in str(exc_info.value), f"Expected ownership error, got: {exc_info.value}"


@pytest.mark.asyncio
async def test_sell_validation_insufficient_shares(db_session: Session, user_factory):
    """Test that users cannot sell more shares than they own"""
    student = user_factory("test-insufficient-shares@example.com")

    account = account_balance.create(db_session, obj_in={
        "user_id": student.id,
        "balance": 10000.00
    })

    quote = await polygon_service.get_latest_quote("AAPL")
    current_price = float(quote['price']) if quote and quote.get('price') else 150.0

    await trading_service.place_order(db_session, student.id, TradeOrderCreate(
        symbol="AAPL",
        quantity=5,
        order_type=OrderTypeEnum.BUY,
        price=current_price
    ))

    with pytest.raises(Exception) as exc_info:
        await trading_service.place_order(db_session, student.id, TradeOrderCreate(
            symbol="AAPL",
            quantity=10,
            order_type=OrderTypeEnum.SELL,
            price=current_price
        ))

    assert "Insufficient shares" in str(exc_info.value), f"Expected insufficient shares error, got: {exc_info.value}"
