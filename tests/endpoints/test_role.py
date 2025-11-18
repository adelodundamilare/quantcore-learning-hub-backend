import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

def test_role_endpoints_smoke(client: TestClient, super_admin_token: str, db_session: Session):
    headers = {"Authorization": f"Bearer {super_admin_token}"}
    
    endpoints = [
        ("GET", "/roles"),
        ("GET", "/roles/1"),
        ("GET", "/roles/1/permissions"),
    ]
    
    for method, endpoint in endpoints:
        response = client.request(method, endpoint, headers=headers)
        assert 200 <= response.status_code < 500

def test_role_operations_smoke(client: TestClient, super_admin_token: str):
    headers = {"Authorization": f"Bearer {super_admin_token}"}
    import uuid
    
    role_data = {
        "name": f"test_role_{uuid.uuid4().hex[:8]}",
        "display_name": "Test Role",
        "description": "Test Role Description"
    }
    
    response = client.post("/roles", json=role_data, headers=headers)
    assert 200 <= response.status_code < 500