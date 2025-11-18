import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

def test_utility_endpoints_smoke(client: TestClient, super_admin_token: str, db_session: Session):
    headers = {"Authorization": f"Bearer {super_admin_token}"}
    
    contact_data = {
        "subject": "Test Subject",
        "message": "Test Message",
        "screenshot_url": None
    }
    
    response = client.post("/utility/contact-admin", json=contact_data, headers=headers)
    assert 200 <= response.status_code < 500