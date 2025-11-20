import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import pytest
from tests.helpers.asserts import api_call

ENDPOINTS=[
    ("GET","/trading/stocks"),
    ("GET","/trading/portfolio"),
    ("GET","/trading/account/balance"),
    ("GET","/trading/watchlists"),
    ("GET","/trading/trade/history"),
    ("GET","/trading/news"),
]

@pytest.mark.parametrize("method,endpoint",ENDPOINTS,ids=[f"{m} {p}" for m,p in ENDPOINTS])
def test_trading_endpoints_smoke(client: TestClient, super_admin_token: str, db_session: Session, method, endpoint):
    headers={"Authorization":f"Bearer {super_admin_token}"}
    api_call(client,method,endpoint,headers=headers,expected_min=200,expected_max=500)

def test_trading_operations_smoke(client: TestClient, super_admin_token: str, db_session):
    headers = {"Authorization": f"Bearer {super_admin_token}"}
    
    watchlist_data = {
        "name": "Test Watchlist",
        "symbols": ["AAPL"]
    }
    
    response = client.post("/trading/watchlists", json=watchlist_data, headers=headers)
    assert 200 <= response.status_code < 500