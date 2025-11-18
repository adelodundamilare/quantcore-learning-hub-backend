import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.constants import ADMIN_SCHOOL_NAME
from app.crud.school import school as crud_school

class TestSchoolEndpoints:
    def test_create_school_smoke(self, client: TestClient, super_admin_token: str):
        unique_email = f"school-admin-{uuid.uuid4()}@test.com"
        response = client.post(
            "/schools",
            headers={"Authorization": f"Bearer {super_admin_token}"},
            json={"school_name": "New School", "admin_email": unique_email, "admin_full_name": "Test Admin"}
        )
        assert 200 <= response.status_code < 500

    def test_read_school_smoke(self, client: TestClient, db_session: Session):
        admin_school = crud_school.get_by_name(db_session, name=ADMIN_SCHOOL_NAME)
        response = client.get(f"/schools/{admin_school.id}")
        assert 200 <= response.status_code < 300

    def test_get_school_students_smoke(self, client: TestClient, super_admin_token: str, db_session: Session):
        admin_school = crud_school.get_by_name(db_session, name=ADMIN_SCHOOL_NAME)
        response = client.get(
            f"/schools/{admin_school.id}/students",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert 200 <= response.status_code <= 500

    def test_get_school_teachers_smoke(self, client: TestClient, super_admin_token: str, db_session: Session):
        admin_school = crud_school.get_by_name(db_session, name=ADMIN_SCHOOL_NAME)
        response = client.get(
            f"/schools/{admin_school.id}/teachers",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert 200 <= response.status_code <= 500

    def test_get_admin_schools_report_smoke(self, client: TestClient, super_admin_token: str):
        response = client.get(
            "/schools/admin/schools/report",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert 200 <= response.status_code < 300

    def test_get_all_schools_admin_smoke(self, client: TestClient, super_admin_token: str):
        response = client.get(
            "/schools/admin/schools",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert 200 <= response.status_code < 300

    def test_update_school_admin_smoke(self, client: TestClient, super_admin_token: str, db_session: Session):
        admin_school = crud_school.get_by_name(db_session, name=ADMIN_SCHOOL_NAME)
        response = client.put(
            f"/schools/admin/schools/{admin_school.id}",
            headers={"Authorization": f"Bearer {super_admin_token}"},
            json={"name": "Updated School Name"}
        )
        assert 200 <= response.status_code < 300

    def test_delete_school_admin_smoke(self, client: TestClient, super_admin_token: str, db_session: Session):
        new_school_name = f"school-to-delete-{uuid.uuid4()}"
        new_school = crud_school.create(db_session, obj_in={"name": new_school_name})
        response = client.delete(
            f"/schools/admin/schools/{new_school.id}",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert 200 <= response.status_code < 300
