"""
Test script to verify cache invalidation for trading operations
"""
import pytest
from fastapi.testclient import TestClient

def test_trading_cache_invalidation(client: TestClient, token_for_role, db_session):
    """Test that trading operations properly invalidate cache"""
    from app.models.trading import AccountBalance
    
    token = token_for_role("super_admin")
    headers = {"Authorization": f"Bearer {token}"}
    
    user_resp = client.get("/account/me", headers=headers)
    assert user_resp.status_code == 200
    user_id = user_resp.json()["data"]["id"]
    
    print(f"\n[0] Adding funds to account")
    balance_obj = db_session.query(AccountBalance).filter(AccountBalance.user_id == user_id).first()
    if balance_obj:
        balance_obj.balance = 10000.0
    else:
        balance_obj = AccountBalance(user_id=user_id, balance=10000.0)
        db_session.add(balance_obj)
    db_session.commit()
    print(f"[PASS] Account funded with $10000")

    symbol = "AAPL"
    quantity = 5
    price = 150.0

    print(f"\n[1] Creating initial position by buying {quantity} shares of {symbol}")
    buy_resp = client.post("/trading/trade/buy", headers=headers, json={
        "symbol": symbol,
        "quantity": quantity,
        "price": price,
        "order_type": "buy"
    })
    assert buy_resp.status_code == 201, f"Buy failed: {buy_resp.text}"
    print(f"[PASS] Buy order succeeded")

    print(f"\n[2] Checking portfolio after buy")
    portfolio_resp = client.get("/trading/portfolio", headers=headers)
    assert portfolio_resp.status_code == 200, f"Portfolio fetch failed: {portfolio_resp.text}"
    initial_portfolio = portfolio_resp.json()["data"]
    print(f"Initial portfolio has {len(initial_portfolio)} position(s)")
    assert len(initial_portfolio) > 0, "Portfolio should have at least one position after buy"

    position = next((p for p in initial_portfolio if p["symbol"] == symbol), None)
    assert position is not None, f"Symbol {symbol} not found in portfolio"
    print(f"[PASS] Found {symbol} with quantity {position.get('quantity', 0)}")

    print(f"\n[3] Selling {quantity} shares of {symbol}")
    sell_resp = client.post("/trading/trade/sell", headers=headers, json={
        "symbol": symbol,
        "quantity": quantity,
        "price": price,
        "order_type": "sell"
    })
    assert sell_resp.status_code == 201, f"Sell failed: {sell_resp.status_code} - {sell_resp.text}"
    print(f"[PASS] Sell order succeeded")

    print(f"\n[4] Checking portfolio after sell (cache should be invalidated)")
    portfolio_resp2 = client.get("/trading/portfolio", headers=headers)
    assert portfolio_resp2.status_code == 200, f"Portfolio fetch failed: {portfolio_resp2.text}"
    updated_portfolio = portfolio_resp2.json()["data"]
    print(f"Updated portfolio has {len(updated_portfolio)} position(s)")

    position_after = next((p for p in updated_portfolio if p["symbol"] == symbol), None)
    if position_after is None or position_after.get("quantity", 0) == 0:
        print(f"[PASS] Cache invalidation working - {symbol} position cleared")
    else:
        assert False, f"Cache may not be invalidated - {symbol} still has quantity {position_after.get('quantity', 0)}"
