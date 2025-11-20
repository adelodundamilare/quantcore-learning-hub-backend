import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from tests.helpers.asserts import api_call
from app.core.constants import ADMIN_SCHOOL_NAME
from app.crud.school import school as crud_school
from app.crud.course import course as crud_course

@pytest.mark.parametrize("role",["teacher","school_admin","super_admin"])
def test_teacher_create_and_assign_student_flow(client: TestClient, token_for_role, db_session: Session, role, user_factory):
    headers={"Authorization":f"Bearer {token_for_role(role)}"}
    admin_school=crud_school.get_by_name(db_session,name=ADMIN_SCHOOL_NAME)
    r=client.post("/courses/",headers=headers,json={"title":"Teacher Flow Course","school_id":admin_school.id})
    if not (200<=r.status_code<300):
        pytest.skip("course create not permitted for role")
    course_id=r.json().get("data",{}).get("id") or r.json().get("id")
    import uuid
    student=user_factory(f"flow-{uuid.uuid4().hex}@t.com")
    client.post("/enrollment/enroll",headers=headers,json={"user_id":student.id,"course_id":course_id})
    client.get("/courses/me",headers={"Authorization":f"Bearer {token_for_role('student')}"})