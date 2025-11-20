import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from tests.helpers.asserts import api_call
from app.core.constants import ADMIN_SCHOOL_NAME
from app.crud.school import school as crud_school
from app.crud.course import course as crud_course

def login(client: TestClient, email: str, password: str = "testpass123") -> str:
    r=client.post("/auth/login",json={"email":email,"password":password})
    b=r.json()
    return b.get("data",{}).get("token",{}).get("access_token") or b.get("token",{}).get("access_token") or b.get("access_token")

@pytest.mark.parametrize("path_tmpl",[
    "/course-progress/courses/{course_id}/progress",
    "/course-progress/courses/{course_id}/completed-lessons",
    "/course-progress/courses/{course_id}/lesson-progress",
])
def test_student_cannot_access_unassigned_course_paths(client: TestClient, token_for_role, db_session: Session, user_factory, path_tmpl):
    headers_admin={"Authorization":f"Bearer {token_for_role('super_admin')}"}
    admin_school=crud_school.get_by_name(db_session,name=ADMIN_SCHOOL_NAME)
    r_course=client.post("/courses/",headers=headers_admin,json={"title":f"Unassigned {uuid.uuid4().hex[:6]}","school_id":admin_school.id})
    assert 200<=r_course.status_code<300
    course_id=r_course.json().get("data",{}).get("id") or r_course.json().get("id")
    student_email=f"matrix-student-{uuid.uuid4().hex}@t.com"
    student=user_factory(student_email)
    student_token=login(client,student_email)
    headers_student={"Authorization":f"Bearer {student_token}"}
    path=path_tmpl.format(course_id=course_id)
    r=client.get(path,headers=headers_student)
    assert r.status_code in (403,404), f"Expected denial for unassigned course, got {r.status_code}"
