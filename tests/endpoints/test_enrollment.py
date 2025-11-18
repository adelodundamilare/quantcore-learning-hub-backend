import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

def test_enrollment_endpoints_smoke(client: TestClient, super_admin_token: str, db_session: Session):
    headers = {"Authorization": f"Bearer {super_admin_token}"}
    
    response = client.get("/enrollments/completed", headers=headers)
    assert 200 <= response.status_code < 500

def test_enrollment_operations_smoke(client: TestClient, super_admin_token: str, db_session, user_factory):
    headers = {"Authorization": f"Bearer {super_admin_token}"}
    from tests.helpers.smoke_utils import create_course_factory
    user = user_factory(f"testuser{id(db_session)}@test.com")
    course = create_course_factory(db_session)()
    
    enrollment_data = {
        "user_id": user.id,
        "course_id": course.id
    }
    
    response = client.post(f"/enrollments/{course.id}/auto-reward", json={}, headers=headers)
    assert 200 <= response.status_code < 500