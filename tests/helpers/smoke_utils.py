from typing import List, Tuple, Dict, Any
from fastapi.testclient import TestClient

def test_endpoints_batch(
    client: TestClient, 
    endpoints: List[Tuple[str, str]], 
    headers: Dict[str, str] = None,
    expected_status_range: Tuple[int, int] = (200, 300)
) -> None:
    for method, endpoint in endpoints:
        response = client.request(method, endpoint, headers=headers)
        assert expected_status_range[0] <= response.status_code < expected_status_range[1], \
            f"{method} {endpoint} returned {response.status_code}"

def test_operations_batch(
    client: TestClient,
    operations: List[Tuple[str, str, Dict[str, Any]]],
    headers: Dict[str, str] = None,
    expected_status_range: Tuple[int, int] = (200, 500)
) -> None:
    for method, endpoint, data in operations:
        response = client.request(method, endpoint, json=data, headers=headers)
        assert expected_status_range[0] <= response.status_code < expected_status_range[1], \
            f"{method} {endpoint} returned {response.status_code}"

def create_test_headers(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"}

def create_school_factory(db_session):
    from app.crud.school import school as crud_school
    def _factory(name=None):
        school_data = {"name": name or f"Test School {id(db_session)}"}
        return crud_school.create(db_session, obj_in=school_data)
    return _factory

def create_course_factory(db_session):
    from app.crud.course import course as crud_course
    from app.models.course import Course
    def _factory(title=None, school_id=None):
        if not school_id:
            school = create_school_factory(db_session)()
            school_id = school.id
        
        course_data = {
            "title": title or f"Test Course {id(db_session)}",
            "description": "Test Description",
            "school_id": school_id
        }
        return crud_course.create(db_session, obj_in=course_data)
    return _factory

READ_ENDPOINTS = [
    ("GET", "/health"),
    ("GET", "/docs"),
    ("GET", "/openapi.json")
]

CRUD_PATTERNS = {
    "list": ("GET", ""),
    "get": ("GET", "/1"),
    "create": ("POST", ""),
    "update": ("PUT", "/1"),
    "delete": ("DELETE", "/1")
}