import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

def test_admin_endpoints_smoke(client: TestClient, super_admin_token: str, db_session: Session):
    headers = {"Authorization": f"Bearer {super_admin_token}"}
    
    endpoints = [
        ("GET", "/admin/users"),
    ]
    
    for method, endpoint in endpoints:
        response = client.request(method, endpoint, headers=headers)
        assert 200 <= response.status_code < 300

def test_admin_operations_smoke(client: TestClient, super_admin_token: str, db_session, user_factory):
    headers = {"Authorization": f"Bearer {super_admin_token}"}
    from tests.helpers.smoke_utils import create_school_factory
    user = user_factory(f"testuser{id(db_session)}@test.com")
    school = create_school_factory(db_session)()
    
    operations = [
        ("PUT", f"/admin/users/{user.id}/status", {"status": "active"}),
        ("PUT", f"/admin/schools/{school.id}/status", {"status": "active"}),
        ("POST", "/admin/bulk-import", {"data": []}),
    ]
    
    for method, endpoint, data in operations:
        response = client.request(method, endpoint, json=data, headers=headers)
        assert 200 <= response.status_code < 500