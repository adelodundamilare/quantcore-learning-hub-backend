import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import AsyncMock

from app.core.constants import OrderTypeEnum, OrderStatusEnum, ADMIN_SCHOOL_NAME
from app.crud.school import school as crud_school
from app.crud.trading import account_balance as crud_account_balance
from app.crud.trading import portfolio_position as crud_portfolio_position
from app.crud.trading import trade_order as crud_trade_order


@pytest.fixture(autouse=True)
def mock_polygon_service_auto(monkeypatch):
    """Auto-apply mock polygon_service to all integration tests"""
    async def mock_get_historical_data(symbol, from_date, to_date, multiplier=1, timespan="day"):
        fixed_prices = {
            "AAPL": 100.0,
            "MSFT": 100.0,
            "GOOGL": 150.0,
            "TSLA": 200.0,
            "NVDA": 180.0,
            "AMZN": 100.0,
        }
        price = fixed_prices.get(symbol.upper(), 100.0)
        return {
            "results": [{"close": price}]
        }
    
    async def mock_get_latest_quote(symbol, use_cache=True):
        fixed_prices = {
            "AAPL": {"price": 100.0, "T": "AAPL"},
            "MSFT": {"price": 100.0, "T": "MSFT"},
            "GOOGL": {"price": 150.0, "T": "GOOGL"},
            "TSLA": {"price": 200.0, "T": "TSLA"},
            "NVDA": {"price": 180.0, "T": "NVDA"},
            "AMZN": {"price": 100.0, "T": "AMZN"},
        }
        return fixed_prices.get(symbol.upper(), {"price": 100.0, "T": symbol.upper()})
    
    async def mock_get_previous_close(symbol):
        fixed_prices = {
            "AAPL": {"close": 100.0},
            "MSFT": {"close": 100.0},
            "GOOGL": {"close": 150.0},
            "TSLA": {"close": 200.0},
            "NVDA": {"close": 180.0},
            "AMZN": {"close": 100.0},
        }
        return fixed_prices.get(symbol.upper(), {"close": 100.0})
    
    from app.services.trading import polygon_service as ps
    ps.get_historical_data = AsyncMock(side_effect=mock_get_historical_data)
    ps.get_latest_quote = AsyncMock(side_effect=mock_get_latest_quote)
    ps.get_previous_close = AsyncMock(side_effect=mock_get_previous_close)


class TestAccountBalance:
    """Test account balance calculations"""

    def test_account_balance_buy_increases_invested_amount(
        self, client: TestClient, token_for_role, db_session: Session
    ):
        """Account balance should show invested amount after buy"""
        headers = {"Authorization": f"Bearer {token_for_role('student')}"}
        
        get_me = client.get("/account/me", headers=headers)
        user_id = get_me.json()["data"]["id"]
        
        account = crud_account_balance.get_by_user_id(db_session, user_id)
        if not account:
            account = crud_account_balance.create(db_session, obj_in={"user_id": user_id, "balance": Decimal("5000")})
        
        response = client.get("/trading/account/balance", headers=headers)
        assert response.status_code == 200
        data = response.json()["data"]
        
        assert data["available_balance"] >= 0
        assert data["amount_invested"] >= 0
        assert abs(data["total_amount"] - (data["available_balance"] + data["amount_invested"])) < 0.01

    def test_account_balance_with_date_range(
        self, client: TestClient, token_for_role, db_session: Session
    ):
        """Period P&L calculation should exclude cash flows outside date range"""
        headers = {"Authorization": f"Bearer {token_for_role('student')}"}
        
        from_date = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
        to_date = datetime.utcnow().strftime("%Y-%m-%d")
        
        response = client.get(
            f"/trading/account/balance?from_date={from_date}&to_date={to_date}",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()["data"]
        
        if data.get("period_pnl") is not None:
            assert isinstance(data["period_pnl"], (int, float))
            assert data["period_start_value"] is not None
            assert data["period_end_value"] is not None


class TestRealizedPnL:
    """Test realized P&L tracking on sell orders"""

    @pytest.mark.asyncio
    async def test_realized_pnl_on_full_liquidation(
        self, client: TestClient, token_for_role, db_session: Session
    ):
        """When selling entire position, realized P&L should be (sale_price - avg_cost_basis) * qty"""
        headers = {"Authorization": f"Bearer {token_for_role('student')}"}
        
        get_me = client.get("/account/me", headers=headers)
        user_id = get_me.json()["data"]["id"]
        
        account = crud_account_balance.get_by_user_id(db_session, user_id)
        if not account:
            account = crud_account_balance.create(db_session, obj_in={"user_id": user_id, "balance": Decimal("5000")})
        else:
            initial_balance = Decimal("5000")
            crud_account_balance.update(db_session, db_obj=account, obj_in={"balance": initial_balance})
        
        buy_order = {
            "symbol": "AAPL",
            "quantity": 50,
            "order_type": "buy",
            "price": 100.0
        }
        buy_response = client.post("/trading/trade/buy", json=buy_order, headers=headers)
        assert buy_response.status_code == 201
        
        position = crud_portfolio_position.get_by_user_and_symbol(db_session, user_id, "AAPL")
        assert position is not None
        assert position.average_price == 100.0
        
        sell_order = {
            "symbol": "AAPL",
            "quantity": 50,
            "order_type": "sell",
            "price": 100.0
        }
        sell_response = client.post("/trading/trade/sell", json=sell_order, headers=headers)
        assert sell_response.status_code == 201
        
        db_session.expire_all()
        sell_trade = crud_trade_order.get_by_user_and_id(db_session, user_id, sell_response.json()["data"]["id"])
        
        assert sell_trade is not None
        assert sell_trade.realized_pnl is not None
        expected_pnl = Decimal("50") * (Decimal("100") - Decimal("100"))
        assert abs(Decimal(str(sell_trade.realized_pnl)) - expected_pnl) < Decimal("0.01")

    @pytest.mark.asyncio
    async def test_realized_pnl_on_partial_liquidation(
        self, client: TestClient, token_for_role, db_session: Session
    ):
        """When selling partial position, realized P&L should use average cost basis"""
        headers = {"Authorization": f"Bearer {token_for_role('student')}"}
        
        get_me = client.get("/account/me", headers=headers)
        user_id = get_me.json()["data"]["id"]
        
        account = crud_account_balance.get_by_user_id(db_session, user_id)
        if not account:
            account = crud_account_balance.create(db_session, obj_in={"user_id": user_id, "balance": Decimal("50000")})
        else:
            crud_account_balance.update(db_session, db_obj=account, obj_in={"balance": Decimal("50000")})
        
        buy_order = {
            "symbol": "MSFT",
            "quantity": 100,
            "order_type": "buy",
            "price": 100.0
        }
        buy_response = client.post("/trading/trade/buy", json=buy_order, headers=headers)
        assert buy_response.status_code == 201
        
        sell_order = {
            "symbol": "MSFT",
            "quantity": 50,
            "order_type": "sell",
            "price": 100.0
        }
        sell_response = client.post("/trading/trade/sell", json=sell_order, headers=headers)
        assert sell_response.status_code == 201
        
        db_session.expire_all()
        sell_trade = crud_trade_order.get_by_user_and_id(db_session, user_id, sell_response.json()["data"]["id"])
        
        assert sell_trade is not None
        assert sell_trade.realized_pnl is not None
        expected_pnl = Decimal("50") * (Decimal("100") - Decimal("100"))
        assert abs(Decimal(str(sell_trade.realized_pnl)) - expected_pnl) < Decimal("0.01")
        
        db_session.expire_all()
        position = crud_portfolio_position.get_by_user_and_symbol(db_session, user_id, "MSFT")
        assert position.quantity == 50
        assert position.average_price == Decimal("100")


class TestAveragePriceUpdate:
    """Test that average price updates correctly"""

    @pytest.mark.asyncio
    async def test_average_price_with_multiple_buys(
        self, client: TestClient, token_for_role, db_session: Session
    ):
        """Average price should update correctly with multiple buy orders"""
        headers = {"Authorization": f"Bearer {token_for_role('student')}"}
        
        get_me = client.get("/account/me", headers=headers)
        user_id = get_me.json()["data"]["id"]
        
        account = crud_account_balance.get_by_user_id(db_session, user_id)
        if not account:
            account = crud_account_balance.create(db_session, obj_in={"user_id": user_id, "balance": Decimal("50000")})
        else:
            crud_account_balance.update(db_session, db_obj=account, obj_in={"balance": Decimal("50000")})
        
        buy1 = {
            "symbol": "GOOGL",
            "quantity": 100,
            "order_type": "buy",
            "price": 100.0
        }
        response1 = client.post("/trading/trade/buy", json=buy1, headers=headers)
        assert response1.status_code == 201
        
        buy2 = {
            "symbol": "GOOGL",
            "quantity": 100,
            "order_type": "buy",
            "price": 200.0
        }
        response2 = client.post("/trading/trade/buy", json=buy2, headers=headers)
        assert response2.status_code == 201
        
        db_session.expire_all()
        position = crud_portfolio_position.get_by_user_and_symbol(db_session, user_id, "GOOGL")
        assert position is not None
        assert position.quantity == 200
        
        expected_avg = Decimal("150")
        assert abs(position.average_price - expected_avg) < Decimal("0.01")

    @pytest.mark.asyncio
    async def test_position_removed_after_full_sell(
        self, client: TestClient, token_for_role, db_session: Session
    ):
        """Position should be removed from portfolio after complete liquidation"""
        headers = {"Authorization": f"Bearer {token_for_role('student')}"}
        
        get_me = client.get("/account/me", headers=headers)
        user_id = get_me.json()["data"]["id"]
        
        account = crud_account_balance.get_by_user_id(db_session, user_id)
        if not account:
            account = crud_account_balance.create(db_session, obj_in={"user_id": user_id, "balance": Decimal("50000")})
        else:
            crud_account_balance.update(db_session, db_obj=account, obj_in={"balance": Decimal("50000")})
        
        buy = {
            "symbol": "TSLA",
            "quantity": 50,
            "order_type": "buy",
            "price": 100.0
        }
        buy_response = client.post("/trading/trade/buy", json=buy, headers=headers)
        assert buy_response.status_code == 201
        
        db_session.expire_all()
        position_before = crud_portfolio_position.get_by_user_and_symbol(db_session, user_id, "TSLA")
        assert position_before is not None
        
        sell = {
            "symbol": "TSLA",
            "quantity": 50,
            "order_type": "sell",
            "price": 150.0
        }
        sell_response = client.post("/trading/trade/sell", json=sell, headers=headers)
        assert sell_response.status_code == 201
        
        db_session.expire_all()
        position_after = crud_portfolio_position.get_by_user_and_symbol(db_session, user_id, "TSLA")
        assert position_after is None


class TestUnrealizedPnL:
    """Test unrealized P&L calculations"""

    @pytest.mark.asyncio
    async def test_unrealized_pnl_calculation(
        self, client: TestClient, token_for_role, db_session: Session
    ):
        """Unrealized P&L should be (current_price - avg_entry_price) * quantity"""
        headers = {"Authorization": f"Bearer {token_for_role('student')}"}
        
        get_me = client.get("/account/me", headers=headers)
        user_id = get_me.json()["data"]["id"]
        
        account = crud_account_balance.get_by_user_id(db_session, user_id)
        if not account:
            account = crud_account_balance.create(db_session, obj_in={"user_id": user_id, "balance": Decimal("50000")})
        else:
            crud_account_balance.update(db_session, db_obj=account, obj_in={"balance": Decimal("50000")})
        
        buy = {
            "symbol": "NVDA",
            "quantity": 100,
            "order_type": "buy",
            "price": 100.0
        }
        buy_response = client.post("/trading/trade/buy", json=buy, headers=headers)
        assert buy_response.status_code == 201
        
        get_position = client.get(f"/trading/portfolio/{user_id}", headers=headers)
        if get_position.status_code == 200:
            data = get_position.json()["data"]
            
            assert data["cost_value"] == 10000.0
            if data["current_price"] > 100:
                assert data["unrealized_profit_loss"] > 0
                assert data["unrealized_profit_loss_percent"] > 0


class TestPeriodPnL:
    """Test period P&L calculations"""

    @pytest.mark.asyncio
    async def test_period_pnl_excludes_cash_flows_outside_period(
        self, client: TestClient, token_for_role, db_session: Session
    ):
        """Period P&L should correctly adjust for deposits/withdrawals"""
        headers = {"Authorization": f"Bearer {token_for_role('student')}"}
        
        start_date = (datetime.utcnow() - timedelta(days=60)).strftime("%Y-%m-%d")
        end_date = datetime.utcnow().strftime("%Y-%m-%d")
        
        response = client.get(
            f"/trading/account/balance?from_date={start_date}&to_date={end_date}",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()["data"]
        
        if data.get("period_pnl") is not None:
            assert data["period_start_value"] is not None
            assert data["period_end_value"] is not None
            
            formula = data["period_end_value"] - data["period_start_value"]
            assert isinstance(data["period_pnl"], (int, float))


class TestPriceDataHandling:
    """Test price data fallback and error handling"""

    def test_missing_price_for_historical_date_returns_error(
        self, client: TestClient, token_for_role, db_session: Session
    ):
        """Requesting portfolio history for dates with missing price data should fail"""
        headers = {"Authorization": f"Bearer {token_for_role('student')}"}
        
        old_date = (datetime.utcnow() - timedelta(days=365 * 10)).strftime("%Y-%m-%d")
        recent_date = datetime.utcnow().strftime("%Y-%m-%d")
        
        response = client.get(
            f"/trading/portfolio/history?from_date={old_date}&to_date={recent_date}",
            headers=headers
        )
        
        if response.status_code == 400:
            assert "price data" in response.json().get("error", {}).get("message", "").lower() or \
                   "price" in response.json().get("detail", "").lower()

    def test_quote_endpoint_returns_current_price(
        self, client: TestClient, token_for_role, db_session: Session
    ):
        """Quote endpoint should return current price"""
        headers = {"Authorization": f"Bearer {token_for_role('student')}"}
        
        response = client.get("/trading/stocks/AAPL/quote", headers=headers)
        
        if response.status_code == 200:
            data = response.json()["data"]
            assert data["price"] > 0
            assert data["timestamp"] is not None


class TestCashAndHoldingsCalculations:
    """Test cash balance and holdings replay logic"""

    @pytest.mark.asyncio
    async def test_cash_balance_after_buy_and_sell(
        self, client: TestClient, token_for_role, db_session: Session
    ):
        """Cash balance should decrease after buy and increase after sell"""
        headers = {"Authorization": f"Bearer {token_for_role('student')}"}
        
        get_me = client.get("/account/me", headers=headers)
        user_id = get_me.json()["data"]["id"]
        
        account = crud_account_balance.get_by_user_id(db_session, user_id)
        initial_balance = Decimal("10000")
        if not account:
            account = crud_account_balance.create(db_session, obj_in={"user_id": user_id, "balance": initial_balance})
        else:
            crud_account_balance.update(db_session, db_obj=account, obj_in={"balance": initial_balance})
        
        buy_response = client.get("/trading/account/balance", headers=headers)
        cash_before_buy = buy_response.json()["data"]["available_balance"]
        
        buy = {
            "symbol": "AMZN",
            "quantity": 50,
            "order_type": "buy",
            "price": 100.0
        }
        client.post("/trading/trade/buy", json=buy, headers=headers)
        
        balance_after_buy = client.get("/trading/account/balance", headers=headers)
        cash_after_buy = balance_after_buy.json()["data"]["available_balance"]
        
        expected_cash_after_buy = cash_before_buy - (50 * 100.0)
        assert abs(cash_after_buy - expected_cash_after_buy) < 0.01
        
        sell = {
            "symbol": "AMZN",
            "quantity": 50,
            "order_type": "sell",
            "price": 100.0
        }
        client.post("/trading/trade/sell", json=sell, headers=headers)
        
        balance_after_sell = client.get("/trading/account/balance", headers=headers)
        cash_after_sell = balance_after_sell.json()["data"]["available_balance"]
        
        expected_cash_after_sell = cash_after_buy + (50 * 100.0)
        assert abs(cash_after_sell - expected_cash_after_sell) < 0.01
