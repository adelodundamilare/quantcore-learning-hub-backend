import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

def test_report_endpoints_smoke(client: TestClient, super_admin_token: str, db_session: Session):
    headers = {"Authorization": f"Bearer {super_admin_token}"}
    
    response = client.get("/reports/admin/dashboard/stats", headers=headers)
    assert 200 <= response.status_code < 500

def test_report_operations_smoke(client: TestClient, super_admin_token: str):
    headers = {"Authorization": f"Bearer {super_admin_token}"}
    
    report_data = {
        "type": "user_activity",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "format": "csv"
    }
    
    response = client.post("/reports/generate", json=report_data, headers=headers)
    assert 200 <= response.status_code < 500
    
    response = client.get("/reports/export/csv", headers=headers)
    assert 200 <= response.status_code < 500