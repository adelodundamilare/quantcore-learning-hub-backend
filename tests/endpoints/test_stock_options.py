import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

def test_stock_options_endpoints_smoke(client: TestClient, super_admin_token: str, db_session: Session):
    headers = {"Authorization": f"Bearer {super_admin_token}"}
    
    endpoints = [
        ("GET", "/stock-options"),
        ("GET", "/stock-options/1"),
        ("GET", "/stock-options/user/1"),
        ("GET", "/stock-options/grants"),
    ]
    
    for method, endpoint in endpoints:
        response = client.request(method, endpoint, headers=headers)
        assert 200 <= response.status_code < 500

def test_stock_options_operations_smoke(client: TestClient, super_admin_token: str, db_session, user_factory):
    headers = {"Authorization": f"Bearer {super_admin_token}"}
    user = user_factory(f"testuser{id(db_session)}@test.com")
    
    grant_data = {
        "user_id": user.id,
        "grant_amount": 1000,
        "strike_price": 10.00,
        "vesting_schedule": "4_year_cliff"
    }
    
    response = client.post("/stock-options/grant", json=grant_data, headers=headers)
    assert 200 <= response.status_code < 500