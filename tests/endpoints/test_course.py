from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.constants import ADMIN_SCHOOL_NAME
from app.crud.school import school as crud_school
from app.crud.course import course as crud_course

class TestCourseEndpoints:
    def test_create_course_smoke(self, client: TestClient, super_admin_token: str, db_session: Session):
        admin_school = crud_school.get_by_name(db_session, name=ADMIN_SCHOOL_NAME)
        response = client.post(
            "/courses/",
            headers={"Authorization": f"Bearer {super_admin_token}"},
            json={"title": "New Course", "description": "A new course", "school_id": admin_school.id}
        )
        assert 200 <= response.status_code < 300

    def test_get_all_courses_smoke(self, client: TestClient, super_admin_token: str):
        response = client.get("/courses/", headers={"Authorization": f"Bearer {super_admin_token}"})
        assert 200 <= response.status_code < 300

    def test_get_my_courses_smoke(self, client: TestClient, super_admin_token: str):
        response = client.get("/courses/me", headers={"Authorization": f"Bearer {super_admin_token}"})
        assert 200 <= response.status_code < 300

    def test_get_courses_by_school_smoke(self, client: TestClient, super_admin_token: str, db_session: Session):
        admin_school = crud_school.get_by_name(db_session, name=ADMIN_SCHOOL_NAME)
        response = client.get(
            f"/courses/by-school/{admin_school.id}",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert 200 <= response.status_code < 300

    def test_read_course_smoke(self, client: TestClient, super_admin_token: str, db_session: Session):
        admin_school = crud_school.get_by_name(db_session, name=ADMIN_SCHOOL_NAME)
        new_course = crud_course.create(db_session, obj_in={"title": "Test Course", "school_id": admin_school.id})
        response = client.get(
            f"/courses/{new_course.id}",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert 200 <= response.status_code < 300

    def test_update_course_smoke(self, client: TestClient, super_admin_token: str, db_session: Session):
        admin_school = crud_school.get_by_name(db_session, name=ADMIN_SCHOOL_NAME)
        new_course = crud_course.create(db_session, obj_in={"title": "Test Course", "school_id": admin_school.id})
        response = client.put(
            f"/courses/{new_course.id}",
            headers={"Authorization": f"Bearer {super_admin_token}"},
            json={"title": "Updated Course Title"}
        )
        assert 200 <= response.status_code < 300

    def test_delete_course_smoke(self, client: TestClient, super_admin_token: str, db_session: Session):
        admin_school = crud_school.get_by_name(db_session, name=ADMIN_SCHOOL_NAME)
        new_course = crud_course.create(db_session, obj_in={"title": "Test Course", "school_id": admin_school.id})
        response = client.delete(
            f"/courses/{new_course.id}",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert 200 <= response.status_code < 300
