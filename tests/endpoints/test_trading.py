import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

def test_trading_endpoints_smoke(client: TestClient, super_admin_token: str, db_session: Session):
    headers = {"Authorization": f"Bearer {super_admin_token}"}
    
    endpoints = [
        ("GET", "/trading/stocks"),
        ("GET", "/trading/portfolio"),
        ("GET", "/trading/account/balance"),
        ("GET", "/trading/watchlists"),
        ("GET", "/trading/trade/history"),
        ("GET", "/trading/news"),
    ]
    
    for method, endpoint in endpoints:
        response = client.request(method, endpoint, headers=headers)
        assert 200 <= response.status_code < 300

def test_trading_operations_smoke(client: TestClient, super_admin_token: str, db_session):
    headers = {"Authorization": f"Bearer {super_admin_token}"}
    
    watchlist_data = {
        "name": "Test Watchlist",
        "symbols": ["AAPL"]
    }
    
    response = client.post("/trading/watchlists", json=watchlist_data, headers=headers)
    assert 200 <= response.status_code < 500