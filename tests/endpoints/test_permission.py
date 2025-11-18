import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

def test_permission_endpoints_smoke(client: TestClient, super_admin_token: str, db_session: Session):
    headers = {"Authorization": f"Bearer {super_admin_token}"}
    
    endpoints = [
        ("GET", "/permissions"),
        ("GET", "/permissions/1"),
        ("GET", "/permissions/user/1"),
        ("GET", "/permissions/role/1"),
    ]
    
    for method, endpoint in endpoints:
        response = client.request(method, endpoint, headers=headers)
        assert 200 <= response.status_code < 500

def test_permission_operations_smoke(client: TestClient, super_admin_token: str, db_session, user_factory):
    headers = {"Authorization": f"Bearer {super_admin_token}"}
    user = user_factory(f"testuser{id(db_session)}@test.com")
    
    operations = [
        ("POST", "/permissions/assign", {"user_id": user.id, "permission_id": 1}),
        ("POST", "/permissions/revoke", {"user_id": user.id, "permission_id": 1}),
        ("POST", "/permissions/role/assign", {"role_id": 1, "permission_id": 1}),
    ]
    
    for method, endpoint, data in operations:
        response = client.request(method, endpoint, json=data, headers=headers)
        assert 200 <= response.status_code < 500