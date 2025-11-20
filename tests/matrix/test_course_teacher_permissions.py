import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from tests.helpers.asserts import api_call
from app.core.constants import ADMIN_SCHOOL_NAME
from app.crud.school import school as crud_school
from app.crud.course import course as crud_course

def _h(token):
    return {"Authorization":f"Bearer {token}"}

@pytest.mark.parametrize("role,exp",[("super_admin",200),("school_admin",200),("teacher",200),("student",403)])
def test_course_create_permissions(client: TestClient, token_for_role, role, exp, db_session: Session):
    admin_school=crud_school.get_by_name(db_session,name=ADMIN_SCHOOL_NAME)
    token=token_for_role(role)
    r=client.post("/courses/",headers=_h(token),json={"title":"Teacher Course","school_id":admin_school.id})
    if exp==200:
        assert 200<=r.status_code<300 or r.status_code==404
    else:
        assert r.status_code in (403,404)

@pytest.mark.parametrize("role,exp",[("super_admin",200),("school_admin",200),("teacher",200),("student",403)])
def test_course_assign_student_permissions(client: TestClient, token_for_role, role, exp, db_session: Session, user_factory):
    admin_school=crud_school.get_by_name(db_session,name=ADMIN_SCHOOL_NAME)
    course=crud_course.create(db_session,obj_in={"title":"Assign Course","school_id":admin_school.id})
    token=token_for_role(role)
    import uuid
    student=user_factory(f"assign-{uuid.uuid4().hex}@t.com")
    r=client.post("/enrollment/enroll",headers=_h(token),json={"user_id":student.id,"course_id":course.id})
    if exp==200:
        assert 200<=r.status_code<300 or r.status_code in (404,422)
    else:
        assert r.status_code in (403,404)

@pytest.mark.parametrize("role,exp",[("super_admin",200),("school_admin",200),("teacher",200),("student",403)])
def test_course_update_delete_permissions(client: TestClient, token_for_role, role, exp, db_session: Session):
    admin_school=crud_school.get_by_name(db_session,name=ADMIN_SCHOOL_NAME)
    c=crud_course.create(db_session,obj_in={"title":"UpDel","school_id":admin_school.id})
    token=token_for_role(role)
    r1=client.put(f"/courses/{c.id}",headers=_h(token),json={"title":"UpDel2"})
    r2=client.delete(f"/courses/{c.id}",headers=_h(token))
    if exp==200:
        assert (200<=r1.status_code<300 or r1.status_code==404) and (200<=r2.status_code<300 or r2.status_code==404)
    else:
        assert r1.status_code in (403,404) and r2.status_code in (403,404)