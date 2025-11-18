import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

def test_billing_endpoints_smoke(client: TestClient, super_admin_token: str, db_session: Session):
    headers = {"Authorization": f"Bearer {super_admin_token}"}
    
    response = client.get("/billing/subscriptions", headers=headers)
    assert 200 <= response.status_code < 500

def test_billing_create_operations_smoke(client: TestClient, super_admin_token: str, db_session):
    headers = {"Authorization": f"Bearer {super_admin_token}"}
    from tests.helpers.smoke_utils import create_school_factory
    school = create_school_factory(db_session)()
    
    create_operations = [
        ("POST", "/billing/create-subscription", {"school_id": school.id, "price_id": "test_price"}),
        ("POST", "/billing/create-invoice", {"school_id": school.id, "amount": 1000}),
    ]
    
    for method, endpoint, data in create_operations:
        response = client.request(method, endpoint, json=data, headers=headers)
        assert 200 <= response.status_code < 500