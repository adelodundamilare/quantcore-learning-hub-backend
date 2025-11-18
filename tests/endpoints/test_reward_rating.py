import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

def test_reward_rating_endpoints_smoke(client: TestClient, super_admin_token: str, db_session: Session):
    headers = {"Authorization": f"Bearer {super_admin_token}"}
    
    endpoints = [
        ("GET", "/rewards"),
        ("GET", "/rewards/1"),
        ("GET", "/ratings"),
        ("GET", "/ratings/course/1"),
    ]
    
    for method, endpoint in endpoints:
        response = client.request(method, endpoint, headers=headers)
        assert 200 <= response.status_code < 500

def test_reward_rating_operations_smoke(client: TestClient, super_admin_token: str, db_session, user_factory):
    headers = {"Authorization": f"Bearer {super_admin_token}"}
    from tests.helpers.smoke_utils import create_course_factory
    user = user_factory(f"testuser{id(db_session)}@test.com")
    course = create_course_factory(db_session)()
    
    reward_data = {
        "user_id": user.id,
        "type": "achievement",
        "title": "Test Reward",
        "description": "Test Description"
    }
    
    response = client.post("/rewards", json=reward_data, headers=headers)
    assert 200 <= response.status_code < 500
    
    rating_data = {
        "user_id": user.id,
        "course_id": course.id,
        "rating": 5,
        "comment": "Great course"
    }
    
    response = client.post("/ratings", json=rating_data, headers=headers)
    assert 200 <= response.status_code < 500