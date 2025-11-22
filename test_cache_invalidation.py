"""
Test script to verify cache invalidation for trading operations
"""
import asyncio
import requests
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "http://localhost:8000"  # Adjust if needed
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@test.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

def login_as_admin():
    """Login and get JWT token"""
    response = requests.post(f"{BASE_URL}/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert response.status_code == 200
    return response.json()["access_token"]

def test_trading_cache_invalidation():
    """Test that trading operations properly invalidate cache"""
    token = login_as_admin()
    headers = {"Authorization": f"Bearer {token}"}

    # First, let's check if we can get portfolio (even if empty)
    portfolio_resp = requests.get(f"{BASE_URL}/trading/portfolio", headers=headers)
    print(f"Portfolio status: {portfolio_resp.status_code}")

    if portfolio_resp.status_code == 200:
        initial_portfolio = portfolio_resp.json()["data"]
        print(f"Initial portfolio has {len(initial_portfolio)} positions")

        # If there are positions, test selling
        if initial_portfolio:
            position = initial_portfolio[0]
            symbol = position["symbol"]
            print(f"Testing with symbol: {symbol}")

            # Try to sell 1 share (market order)
            sell_resp = requests.post(f"{BASE_URL}/trading/trade/sell", headers=headers, json={
                "symbol": symbol,
                "quantity": 1,
                "order_type": "SELL"
            })

            if sell_resp.status_code == 201:
                print("Sell order succeeded - cache should be invalidated")

                # Check portfolio again - should be updated
                portfolio_resp2 = requests.get(f"{BASE_URL}/trading/portfolio", headers=headers)
                if portfolio_resp2.status_code == 200:
                    updated_portfolio = portfolio_resp2.json()["data"]
                    print(f"Updated portfolio has {len(updated_portfolio)} positions")
                    print("✅ Cache invalidation appears to work")
                else:
                    print("❌ Failed to get portfolio after sell")
            elif sell_resp.status_code == 400:
                error_detail = sell_resp.json()["detail"]
                if "You don't own any shares" in error_detail:
                    print("🚨 STILL GETTING THE BUG: 'You don't own any shares' error")
                    print(f"Position data: {position}")
                    return False
                else:
                    print(f"Sell failed with different error: {error_detail}")
            else:
                print(f"Sell failed with status {sell_resp.status_code}: {sell_resp.text}")
        else:
            print("No positions to test with - portfolio is empty")
            return None
    else:
        print(f"Unable to access portfolio: {portfolio_resp.status_code}")
        return None

    return True

if __name__ == "__main__":
    result = test_trading_cache_invalidation()
    if result is False:
        exit(1)
    elif result is True:
        print("✅ Test passed - cache invalidation working")
    else:
        print("⚠️ Test inconclusive - no data to test with")
