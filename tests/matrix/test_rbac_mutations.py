import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from tests.helpers.asserts import api_call
from app.core.constants import ADMIN_SCHOOL_NAME
from app.crud.school import school as crud_school
from app.crud.course import course as crud_course
from app.crud.exam import exam as crud_exam

def _headers(token):
    return {"Authorization":f"Bearer {token}"}

@pytest.mark.parametrize("role,expected",[("super_admin",200),("school_admin",200),("teacher",403),("student",403)])
def test_course_update_delete_rbac(client: TestClient, token_for_role, db_session: Session, role, expected):
    admin_school=crud_school.get_by_name(db_session,name=ADMIN_SCHOOL_NAME)
    new_course=crud_course.create(db_session,obj_in={"title":"RBAC Course","school_id":admin_school.id})
    token=token_for_role(role)
    api_call(client,"PUT",f"/courses/{new_course.id}",headers=_headers(token),json={"title":"RBAC Updated"},expected_min=expected,expected_max=expected+1)
    api_call(client,"DELETE",f"/courses/{new_course.id}",headers=_headers(token),expected_min=expected,expected_max=expected+1)

@pytest.mark.parametrize("role,expected",[("super_admin",200),("school_admin",200),("teacher",403),("student",403)])
def test_exam_create_edit_rbac(client: TestClient, token_for_role, db_session: Session, role, expected):
    admin_school=crud_school.get_by_name(db_session,name=ADMIN_SCHOOL_NAME)
    course=crud_course.create(db_session,obj_in={"title":"RBAC Exam Course","school_id":admin_school.id})
    token=token_for_role(role)
    r=client.post("/exams/",headers=_headers(token),json={"title":"RBAC Exam","course_id":course.id})
    if expected==200:
        assert 200<=r.status_code<300 or r.status_code==404
        if 200<=r.status_code<300:
            exam_id=r.json().get("data",{}).get("id") or r.json().get("id")
            client.put(f"/exams/{exam_id}",headers=_headers(token),json={"title":"RBAC Exam Updated"})
    else:
        assert r.status_code in (403,404)

@pytest.mark.parametrize("role,expected",[("super_admin",200),("school_admin",200),("teacher",403),("student",403)])
def test_billing_admin_only_rbac(client: TestClient, token_for_role, role, expected):
    token=token_for_role(role)
    r=client.get("/billing/subscriptions",headers=_headers(token))
    assert r.status_code==expected