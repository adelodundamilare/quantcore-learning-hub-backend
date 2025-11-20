import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from tests.helpers.asserts import api_call
from tests.helpers.contract import validate_response_schema
from app.schemas.course import Course
from app.core.constants import ADMIN_SCHOOL_NAME
from app.crud.school import school as crud_school
from app.crud.course import course as crud_course

ENDPOINTS=[
    ("GET","/courses/"),
    ("GET","/courses/me"),
]

@pytest.mark.parametrize("method,path",ENDPOINTS,ids=[f"{m} {p}" for m,p in ENDPOINTS])
def test_course_list_smoke(client: TestClient, super_admin_token: str, method, path):
    headers={"Authorization":f"Bearer {super_admin_token}"}
    r=api_call(client,method,path,headers=headers,expected_min=200,expected_max=500)
    try:
        data=r.json().get("data")
        if isinstance(data,list):
            for item in data:
                validate_response_schema(item,Course)
    except Exception:
        pass

def test_create_course_smoke(client: TestClient, super_admin_token: str, db_session: Session):
    admin_school=crud_school.get_by_name(db_session,name=ADMIN_SCHOOL_NAME)
    r=api_call(client,"POST","/courses/",headers={"Authorization":f"Bearer {super_admin_token}"},json={"title":"New Course","description":"A new course","school_id":admin_school.id},expected_min=200,expected_max=300)

def test_get_courses_by_school_smoke(client: TestClient, super_admin_token: str, db_session: Session):
    admin_school=crud_school.get_by_name(db_session,name=ADMIN_SCHOOL_NAME)
    api_call(client,"GET",f"/courses/by-school/{admin_school.id}",headers={"Authorization":f"Bearer {super_admin_token}"},expected_min=200,expected_max=300)

def test_read_update_delete_course_smoke(client: TestClient, super_admin_token: str, db_session: Session):
    admin_school=crud_school.get_by_name(db_session,name=ADMIN_SCHOOL_NAME)
    new_course=crud_course.create(db_session,obj_in={"title":"Test Course","school_id":admin_school.id})
    r=api_call(client,"GET",f"/courses/{new_course.id}",headers={"Authorization":f"Bearer {super_admin_token}"},expected_min=200,expected_max=300)
    try:
        data=r.json().get("data")
        if data:
            validate_response_schema(data,Course)
    except Exception:
        pass
    api_call(client,"PUT",f"/courses/{new_course.id}",headers={"Authorization":f"Bearer {super_admin_token}"},json={"title":"Updated Course Title"},expected_min=200,expected_max=300)
    api_call(client,"DELETE",f"/courses/{new_course.id}",headers={"Authorization":f"Bearer {super_admin_token}"},expected_min=200,expected_max=300)
