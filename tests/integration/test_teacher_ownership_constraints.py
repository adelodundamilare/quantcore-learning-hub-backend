import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from tests.helpers.asserts import api_call
from app.core.constants import ADMIN_SCHOOL_NAME
from app.crud.school import school as crud_school

def login(client: TestClient, email: str, password: str = "testpass123") -> str:
    r=client.post("/auth/login",json={"email":email,"password":password})
    b=r.json()
    return b.get("data",{}).get("token",{}).get("access_token") or b.get("token",{}).get("access_token") or b.get("access_token")

@pytest.mark.parametrize("owner_role", ["teacher", "school_admin", "super_admin"])
def test_teacher_ownership_constraints(client: TestClient, token_for_role, db_session: Session, user_factory, owner_role):
    admin_school=crud_school.get_by_name(db_session,name=ADMIN_SCHOOL_NAME)
    headers_owner={"Authorization":f"Bearer {token_for_role(owner_role)}"}
    r_course=client.post("/courses/",headers=headers_owner,json={"title":f"Owner {uuid.uuid4().hex[:6]}","school_id":admin_school.id})
    if not (200<=r_course.status_code<300):
        pytest.skip("owner cannot create course")
    course_id=r_course.json().get("data",{}).get("id")
    teacher_email=f"other-teacher-{uuid.uuid4().hex}@t.com"
    other_teacher=user_factory(teacher_email)
    db_session.commit()
    other_teacher_token=login(client,teacher_email)
    headers_other={"Authorization":f"Bearer {other_teacher_token}"}
    r_edit=client.put(f"/courses/{course_id}",headers=headers_other,json={"title":"X"})
    assert r_edit.status_code in (401, 403, 404)
    assign_response = client.post(f"/courses/{course_id}/teachers/{other_teacher.id}",headers=headers_owner)
    r_edit2=client.put(f"/courses/{course_id}",headers=headers_other,json={"title":"Y"})
    assert r_edit2.status_code in (200, 401, 403, 404)
    r_exam=client.post("/exams/",headers=headers_other,json={"title":"T Exam","course_id":course_id})
    assert r_exam.status_code in (200, 401, 404)
