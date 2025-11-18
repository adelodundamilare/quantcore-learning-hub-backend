import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

def test_account_endpoints_smoke(client: TestClient, super_admin_token: str, db_session: Session):
    headers = {"Authorization": f"Bearer {super_admin_token}"}
    
    endpoints = [
        ("GET", "/account/me"),
        ("GET", "/account/users/admins"),
    ]
    
    for method, endpoint in endpoints:
        response = client.request(method, endpoint, headers=headers)
        assert 200 <= response.status_code < 300

def test_account_operations_smoke(client: TestClient, super_admin_token: str):
    headers = {"Authorization": f"Bearer {super_admin_token}"}
    
    response = client.put("/account/me", json={"full_name": "Updated User"}, headers=headers)
    assert 200 <= response.status_code < 500