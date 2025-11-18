from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.core.constants import ADMIN_SCHOOL_NAME
from app.crud.school import school as crud_school
from app.crud.course import course as crud_course
from app.crud.exam import exam as crud_exam

class TestExamEndpoints:
    def test_create_exam_smoke(self, client: TestClient, super_admin_token: str, db_session: Session):
        admin_school = crud_school.get_by_name(db_session, name=ADMIN_SCHOOL_NAME)
        course = crud_course.create(db_session, obj_in={"title": "Test Course", "school_id": admin_school.id})
        response = client.post(
            "/exams/",
            headers={"Authorization": f"Bearer {super_admin_token}"},
            json={"title": "New Exam", "description": "A new exam", "course_id": course.id}
        )
        assert 200 <= response.status_code < 300

    def test_get_all_exams_smoke(self, client: TestClient, super_admin_token: str):
        response = client.get("/exams/", headers={"Authorization": f"Bearer {super_admin_token}"})
        assert 200 <= response.status_code < 300

    def test_get_exam_smoke(self, client: TestClient, super_admin_token: str, db_session: Session):
        admin_school = crud_school.get_by_name(db_session, name=ADMIN_SCHOOL_NAME)
        course = crud_course.create(db_session, obj_in={"title": "Test Course", "school_id": admin_school.id})
        exam = crud_exam.create(db_session, obj_in={"title": "Test Exam", "course_id": course.id})
        response = client.get(
            f"/exams/{exam.id}",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert 200 <= response.status_code < 300

    def test_update_exam_smoke(self, client: TestClient, super_admin_token: str, db_session: Session):
        admin_school = crud_school.get_by_name(db_session, name=ADMIN_SCHOOL_NAME)
        course = crud_course.create(db_session, obj_in={"title": "Test Course", "school_id": admin_school.id})
        exam = crud_exam.create(db_session, obj_in={"title": "Test Exam", "course_id": course.id})
        response = client.put(
            f"/exams/{exam.id}",
            headers={"Authorization": f"Bearer {super_admin_token}"},
            json={"title": "Updated Exam Title"}
        )
        assert 200 <= response.status_code < 300

    def test_delete_exam_smoke(self, client: TestClient, super_admin_token: str, db_session: Session):
        admin_school = crud_school.get_by_name(db_session, name=ADMIN_SCHOOL_NAME)
        course = crud_course.create(db_session, obj_in={"title": "Test Course", "school_id": admin_school.id})
        exam = crud_exam.create(db_session, obj_in={"title": "Test Exam", "course_id": course.id})
        response = client.delete(
            f"/exams/{exam.id}",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert 200 <= response.status_code < 300

    def test_get_exam_questions_smoke(self, client: TestClient, super_admin_token: str, db_session: Session):
        admin_school = crud_school.get_by_name(db_session, name=ADMIN_SCHOOL_NAME)
        course = crud_course.create(db_session, obj_in={"title": "Test Course", "school_id": admin_school.id})
        exam = crud_exam.create(db_session, obj_in={"title": "Test Exam", "course_id": course.id})
        response = client.get(
            f"/exams/{exam.id}/questions",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert 200 <= response.status_code < 300

    def test_create_questions_smoke(self, client: TestClient, super_admin_token: str, db_session: Session):
        admin_school = crud_school.get_by_name(db_session, name=ADMIN_SCHOOL_NAME)
        course = crud_course.create(db_session, obj_in={"title": "Test Course", "school_id": admin_school.id})
        exam = crud_exam.create(db_session, obj_in={"title": "Test Exam", "course_id": course.id})
        response = client.post(
            f"/exams/{exam.id}/questions",
            headers={"Authorization": f"Bearer {super_admin_token}"},
            json=[{"text": "What is 2+2?", "options": ["3", "4", "5"], "correct_answer": "4"}]
        )
        assert 200 <= response.status_code < 500

    def test_start_exam_attempt_smoke(self, client: TestClient, super_admin_token: str, db_session: Session):
        admin_school = crud_school.get_by_name(db_session, name=ADMIN_SCHOOL_NAME)
        course = crud_course.create(db_session, obj_in={"title": "Test Course", "school_id": admin_school.id})
        exam = crud_exam.create(db_session, obj_in={"title": "Test Exam", "course_id": course.id, "is_active": True})
        response = client.post(
            f"/exams/exams/{exam.id}/attempts",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        assert 200 <= response.status_code < 500
