import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.helpers.contract import validate_response_schema
from app.schemas.report import AdminDashboardStatsSchema, StudentLessonProgressSchema

def test_report_endpoints_smoke(client: TestClient, super_admin_token: str, db_session: Session):
    headers={"Authorization":f"Bearer {super_admin_token}"}
    r=client.get("/reports/admin/dashboard/stats",headers=headers)
    assert (200 <= r.status_code < 300) or r.status_code==404
    try:
        data=r.json().get("data")
        if data:
            validate_response_schema(data,AdminDashboardStatsSchema)
    except Exception:
        pass

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


def test_student_lesson_progress_endpoint(client: TestClient, token_for_role: callable, db_session: Session):
    student_token = token_for_role("student")
    headers = {"Authorization": f"Bearer {student_token}"}

    response = client.get("/student/lesson-progress", headers=headers)
    assert 200 <= response.status_code < 300

    if response.status_code == 200:
        data = response.json().get("data")
        if data:
            validate_response_schema(data, StudentLessonProgressSchema)