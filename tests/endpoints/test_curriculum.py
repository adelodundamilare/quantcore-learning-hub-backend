import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

def test_curriculum_endpoints_smoke(client: TestClient, super_admin_token: str, db_session: Session):
    headers = {"Authorization": f"Bearer {super_admin_token}"}
    
    endpoints = [
        ("GET", "/curriculum"),
        ("GET", "/curriculum/1"),
        ("GET", "/curriculum/1/lessons"),
    ]
    
    for method, endpoint in endpoints:
        response = client.request(method, endpoint, headers=headers)
        assert 200 <= response.status_code < 500

def test_curriculum_create_operations_smoke(client: TestClient, super_admin_token: str, db_session):
    headers = {"Authorization": f"Bearer {super_admin_token}"}
    from tests.helpers.smoke_utils import create_course_factory
    course = create_course_factory(db_session)()
    
    curriculum_data = {
        "title": "Test Curriculum",
        "description": "Test Description",
        "course_id": course.id
    }
    
    response = client.post("/curriculum", json=curriculum_data, headers=headers)
    assert 200 <= response.status_code < 500