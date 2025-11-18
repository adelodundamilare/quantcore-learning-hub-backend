import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

def test_course_progress_endpoints_smoke(client: TestClient, super_admin_token: str, db_session: Session):
    headers = {"Authorization": f"Bearer {super_admin_token}"}
    
    endpoints = [
        ("GET", "/course-progress"),
        ("GET", "/course-progress/1"),
        ("GET", "/course-progress/1/lessons"),
    ]
    
    for method, endpoint in endpoints:
        response = client.request(method, endpoint, headers=headers)
        assert 200 <= response.status_code < 500

def test_course_progress_operations_smoke(client: TestClient, super_admin_token: str, db_session, user_factory):
    headers = {"Authorization": f"Bearer {super_admin_token}"}
    from tests.helpers.smoke_utils import create_course_factory
    user = user_factory(f"testuser{id(db_session)}@test.com")
    course = create_course_factory(db_session)()
    
    progress_data = {
        "user_id": user.id,
        "course_id": course.id,
        "lesson_id": 1,
        "completed": True
    }
    
    response = client.post("/course-progress/update", json=progress_data, headers=headers)
    assert 200 <= response.status_code < 500
    
    response = client.get(f"/course-progress/user/{user.id}/course/{course.id}", headers=headers)
    assert 200 <= response.status_code < 500